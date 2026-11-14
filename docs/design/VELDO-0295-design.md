# VELDO-0295 design: space management

Revision 6, 2026-11-13. Design for the spec at
specs/VELDO-0295-veldo-records-what-it-creates-and-removes-it-at-the-event-that-ends-it.md. It answers
the owner's request (Telegram 41152): "for veldo we need to introduce space management - with all of the
projects, worktrees and tmp growing, veldo needs to clean things up after itself. this should happen not
just like once in a while, but we need to keep track of things that are created, changed, merged, etc and
have it part of the process".

The design in one paragraph: Veldo keeps a ledger in its control store. Every thing a Veldo process makes
on disk or in Docker is written to the ledger before it is made, with its owner and the events that end
it. Things made by processes Veldo does not start (a worktree someone adds with git, a gate run from a
shell, a lead session, a builder started by a script) are recorded by a hook or a wrapper that runs inside
that process. When an ending event happens, the things it ends are removed at once, each through a fixed
set of safety rules: by the emitting process itself when that process is a run, a gate or a landing
station, and by the authority service when the event came from a git hook or a session hook, which only
record and return. A thing a rule refuses stays, is marked deferred with the rule's name, and is tried
again at its next event. A run states the space it needs and waits when the pool cannot cover it. At
service start, and when asked, Veldo compares the disk and Docker with the ledger. There is no timer
anywhere in it, and nothing in Veldo is removed because of its age.

Revision 2 followed the first validation of 2026-11-13 (B1 to B6, M1 to M9). Revision 3 followed the
second (R1 to R4, S1 to S11). Revision 4 followed the third (C1 to C6 and D1 to D7). Revision 5 followed
the fourth (E1 to E3 and F1 to F6). Revision 6 follows the fifth (verdict CHANGES, G1 to G4) and carries
the lead's decisions (f), (g) and (h) exactly. Section 14 answers the points of all five.

Amended 2026-11-13, after the review of VELDO-0298 and VELDO-0299 (verdict FIX for both), by the lead's
decisions. The amendment is in section 7, under "What a probe cannot read" and "A child holds its
parent", in rules 4, 5 and 6 of its table, and in the children rule of section 5:

- Every probe fails closed. What it cannot read or cannot decide is in use, or is unique work, never
  free.
- A process the probe may not read counts as use of an item only when it could reach that item (bounded
  fail closed).
- A kept, declared or removing child holds its parent. The review removed an agent repository with a
  kept worktree, and its uncommitted files, inside it.

Amended again 2026-11-13, after the re-review (VELDO-0298 accepted; FIX for VELDO-0299 and VELDO-0330),
in the same places of section 7:

- A privileged process (root, or one whose capabilities pass every mode check) that a login started
  counts for every item, read from its loginuid. Only a system daemon is judged by the mode, and that
  is a stated policy. A kernel thread is left out by its flag, a container's process is judged by its
  container's mounts, and the file-sharing helper is pinned by its identity.
- A git repository on disk beneath a worktree or an agent repository holds it. The re-review deleted
  one, with its only commit, through an ignored folder.
- The "nine processes" measurement is corrected: one of the six was a container's, not the user's.

Amended a third time 2026-11-13, by the owner's decision (Telegram 41204 and 41205), in the new
section 7.1, in 6.8, in sections 3, 12, 13 and 15:

- The probe reads the processes it cannot read itself through the process reader, a small separate
  program with the one file capability cap_sys_ptrace, installed by the owner. No list of process
  names, and the service never holds the capability. Without the reader the bound decides as before.
- One capability does not list a process's open files by path; that was measured. The reader prints
  device and inode numbers, and the probe matches them against the item's own files.
- It is one more ticket, VELDO-0344, built before anything removes on a real host.

What changed in revision 6:

- One answer still covers a day's whole review group, and the request now also offers an answer for one
  worktree of the group (4.9, section 7, VELDO-0342).
- Discard never loses a commit. A detached worktree's commits are put on a kept branch before the
  worktree goes, and only uncommitted changes are discarded (6.5, section 7, VELDO-0343).
- The volumes seoeng_cms-postgres-data and docker_minio_data are rows of the protect list (section 11).
- A review group is keyed by scope, day and a sequence number. A group closes when it is answered, and
  a deferral later that day opens a new one (4.9, section 7, VELDO-0342).

What changed in revision 5:

- The switch to act is also refused while the scope has a pending group the owner has neither confirmed
  nor marked wrong, and, for a bound project, while its gate script lacks the space steps (6.1, section
  11, VELDO-0339).
- A review's worktree is cleaned at the review's end with no request: its stray untracked files are
  review scratch. Any other unique work in review worktrees goes into one grouped decision request per
  day, never one per worktree (section 5, section 7, 8.5, VELDO-0336 and VELDO-0340).
- The protect list is complete: everything of the places project on both engines, the desktop engine's
  disk image, every database volume with real data, and the two images that cannot be pulled again.
  Each is identified by name and by compose label, and nothing on the list is ever proposed or removed
  (section 7, section 11, VELDO-0341).
- Smaller corrections: where the boundary check sits in the build order and that it needs approval,
  the reader that still uses the gate's 30-day value, how the Discard warning is shown, one more
  falsifier and one citation (6.10, section 7, section 12).

What changed in revision 4:

- Report or act is set per project, not for the installation. The owner can mark a proposal wrong, and
  the switch to act is refused until the project has three consecutive clean days in report mode. core's
  gate gets the space steps first, core goes to act first, and the other projects follow the same way
  (section 2, 4.7, 4.8, 6.6, section 11, VELDO-0331 and VELDO-0332).
- No removal by age exists in Veldo, with or without an installation. The sandbox's stale scratch pass
  is deleted and the gate's leg-time store loses its 30-day branch (6.10, VELDO-0324, VELDO-0333).
- A unit waiting for space is judged again only after a write that frees space: a removal that finished,
  or a run that ended and gave back its hold. A pass woken by a timer does nothing for it (6.7,
  VELDO-0334).
- Save, Keep and Discard are offered through the pick form the settlement code already has, so the
  closed set of rulings does not change (section 7, VELDO-0327).
- The review script's throwaway worktree is owned by its run and removed at run finished. The host's
  sandbox script reports "released by its creator", an event a host principal may sign (section 5, 6.9,
  6.10, VELDO-0335 and VELDO-0336).

What changed in revision 3:

- A hand landing removes nothing inside the git command. The hook records the landing and returns; the
  authority service consumes the record and removes the contained worktrees right after (6.9, 8.4).
  Session hooks work the same way.
- The data model has a third owner value, no project, for a session started outside every project (4.1).
- An existing project's gate script is that project's own file and is not changed by a change to the
  engine's. Each bound project's gate gets the three space steps by its own change, reconcile reports a
  gate that lacks them, and until then the run wrapper covers the gate (8.2, section 11, VELDO-0325).
- The table of existing removal paths gains the batch clone, the sandbox's scratch removers and four
  reviewed-list entries (6.10).

Six things the lead must know before reading on:

1. Things an agent's own commands create inside a run (a build folder, a container its tests start)
   cannot be recorded before they exist, because Veldo does not run those commands. They are recorded at
   the run's next event by a census of the run's worktree, its scratch root and its Docker label
   (sections 6.3 and 6.4). Nothing is removed before it is recorded.
2. A Docker object is owned by a run only when it carries the run's label or its compose project name, or
   when compose's own labels or a bind mount place it inside a recorded worktree. An object with none of
   these is reported and never removed (section 6.4).
3. Removal inside a container engine that keeps its data in a disk image frees space inside the image
   and none on the host. The ledger records the two figures apart, and admission for such an engine is
   judged inside it (section 4.2).
4. The first reconcile on an existing host removes nothing. Every project starts in report mode: Veldo
   lists what is due, and the owner confirms per project and kind (section 11). In report mode admission
   only advises. A project goes to act mode by the owner's command, after three clean report days and
   with no pending group left unanswered.
5. Five of the tickets change protected files: the gate script (VELDO-0309, and VELDO-0304, whose check
   is called from this repository's gate script), the sandbox (VELDO-0302 and VELDO-0324) and the gate's
   leg timing (VELDO-0333). Each needs the owner's recorded approval. VELDO-0325 changes the gate script
   of each bound project, which is protected in that project and needs the owner's approval there.
6. Removals that follow a hook's event need the authority service running. The measured host runs none
   today; migration step 1 starts it. Until it runs, hook events wait in a spool and nothing is lost.

## 1. What was measured

Measured read only on the owner's host on 2026-11-13. This section is provenance; the generic documents
carry none of these names.

| What | Measured |
| :- | :- |
| Filesystem | One filesystem of 915 GB holding the home folder and the temporary folder. 29 GB free when revision 1 was written, 61 GB free when revision 2 was written |
| Gate scripts of the bound projects | Each project's scripts/verify.sh is its own file: 485 lines in core, 159 to 251 in the seven others read. None calls the gate host, and no project has a gate_host.json |
| Worktree roots | 13 folders named after a repository with the suffix -worktrees. Nine repositories run Veldo; the rest are plain git repositories |
| core worktrees | 102 in git's list, 157 GB under the worktree root |
| Build folders in them | 8 folders, 89 GB together; the largest 35 GB, then 21 GB and 9 GB; two are named target-veldo1810, not target |
| veldo worktrees | 78 in git's list, 12 GB |
| seo worktrees | 8 in git's list, 5.4 GB |
| Session scratch under the temporary folder | 11 GB in 366 entries |
| Gate logs and evidence under the gate lock's folder | 5.8 GB in 92 entries |
| System Docker engine (context default) | 13 containers, 51 volumes, 80 images (44 GB), 12 GB build cache; its data root is on the host filesystem |
| Desktop Docker engine (context desktop-linux) | 52 containers, 325 volumes (175 GB), 115 images (60 GB), 14 GB build cache; its data is one disk image file on the host |
| Containers with a compose project label, desktop engine | 49 of 52 (not checked again by the validator) |

Who creates the disk use on this host today. None of them emits a Veldo event, no authority service runs
and there is no installation folder:

| Creator | What it makes | How it runs |
| :- | :- | :- |
| Lead sessions | Worktrees added by hand, landing branches, session scratch | A person or a session types git commands |
| Builder runs | Build folders of 5 to 16 GB, scratch, containers | myday/scripts/claude_run.sh:41 and codex_run.sh:32 start a client in a folder |
| Confined builder and review runs | Private repositories, worktrees, a throwaway review worktree | codex_work.sh:130-132 and codex_review.sh:55 call git's worktree add; agent_sandbox.sh:257-266 makes the private repository |
| Gates | 42 to 51 GB of build output each, logs | gate_core_cand.sh:33-37 runs the project's verify.sh under the host lock. The project has no gate_host.json |
| Runs queued on the host lock | Whatever the command builds | host_heavy.sh:9 runs any command under the same lock |
| Manual landings | Landing branches that contain ticket branches | Commits on a landing branch, typed by hand |

What exists today, and the case each one misses:

| Mechanism | What it does | What it misses |
| :- | :- | :- |
| nightly_build_cleanup.sh, user schedule 03:17 | Removes build folders, session scratch and build caches unchanged for 2 days and at least 100 MB, after an in-use check | Acts by age. A folder made and finished today stays two days. It knows no owner, so it cannot tell a landed ticket from a live one. It never touches worktrees or Docker. Its in-use check counts a command line that names the path, which also matches the shell doing the check |
| The gate script | Refuses under 60 GB free, deletes its build folder after the verdict | One script on one project. A gate that fails on a full disk still prints a red verdict and only warns after it |
| Builder briefs | Tell the builder to remove its own output | An instruction. A run killed by a full disk removes nothing |
| Manual cleanup | Took the veldo and seo roots from 116 and 44 worktrees to 78 and 8 | Needs a person, and the person has to work out by hand what is safe |

The standing owner decisions this design obeys: nothing that is in use is removed (33341); the places data
is never touched on either engine (32807); a Docker cleanup is never called safe without listing what it
removes, and the figure a Docker tool calls reclaimable is never quoted as a gain (35405); images that
cannot be pulled again are kept (2026-11-13); the desktop engine's disk image is not acted on.

## 2. Terms

| Term | Meaning |
| :- | :- |
| Item | One thing on disk or in Docker that the ledger has a record for |
| Kind | What an item is: worktree, branch, agent repository, build output, scratch, evidence, container, volume, network, image tag |
| Agent repository | The private git repository the sandbox makes for one agent. The agent's worktree belongs to it, and its commits reach the shared repository only when the runner brings them across |
| Owner | Who an item belongs to. The first part is always one of three: a project, a plain repository, or no project. Where they apply, a ticket, a run, a gate, a lane and a session are added |
| No project | The owner value for scratch of a session whose working folder is inside no bound project and no plain repository. It belongs to the installation. Only session scratch can have it |
| Plain repository | A git repository the installation names that does not run Veldo. It has no tickets and no gate; its worktrees are still recorded |
| Pool | One body of storage whose free space is one number: a filesystem, or a container engine that keeps its data in its own disk image |
| Ending event | An event in the item's lifecycle at which the table in section 5 says to act |
| Due | An ending event has happened and the action has not been carried out yet |
| Deferred | Due, tried, refused by a safety rule; waits for its next event |
| Hold | The space an admitted run has been promised and has not yet used or given back |
| Floor | The free space a pool must keep after every admitted run has taken what it declared |
| Census | Reading what a run left behind (its worktree's untracked folders, its scratch root, its labelled Docker objects) and recording it |
| Protect list | Paths, Docker object names and compose project names that are never recorded, adopted, proposed or removed (section 7) |
| Start commit | The commit a branch pointed at when its item was recorded |
| Space worker | A short-lived child process of the authority service that carries out the removals an event made due, so the service keeps answering while a large folder is deleted |
| Host principal | A signing identity that belongs to the host and not to a person. The service and the receiver each have one today; this design adds two |
| Scope | The first part of an owner: one project, one plain repository, or no project. Mode is kept per scope |
| Mode | report or act, one value per scope, kept as a ledger record (4.7). A scope with no mode record is in report mode. In report mode Veldo proposes and removes only what the owner confirms, and admission advises. In act mode removals happen at events and admission blocks. "In report mode" and "in act mode" in this document always mean the mode of the scope the item or the run belongs to |
| Proposal | Something Veldo shows the owner in report mode and would do by itself in act mode: an item made due, an adoption by reconcile, or an owner proposed for a Docker object |
| Wrong proposal | A proposal the owner marked wrong, with a reason. It is a record (4.8) |
| Clean report day | A calendar day in the installation's time zone on which the scope was in report mode, Veldo handled at least one event or reconcile for it, and the owner marked none of its proposals wrong |
| Pending group | The due items of one scope and one kind, in report mode. It is unconfirmed while it holds an item the owner has neither confirmed nor marked wrong (6.1) |
| Station | What a run is for: build, review or gate. The receiver and the run wrapper name it when they declare the run |
| Review worktree | A detached worktree added inside a run whose station is review. It is a read-only checkout: a review reads the code in it and writes its report elsewhere |
| Review scratch | An untracked file or folder in a review worktree that git does not ignore. It is removed at the review's end with no request (section 7) |

## 3. Components

engine/ is the canon. Every file under engine/.veldo has a synced copy under .veldo, and
engine/scripts/agent_sandbox.py and gate_host.py have copies under scripts/; the copies change with the
canon and the gate's template-sync check fails if they drift.

The gate script is the exception. engine/scripts/verify.sh is the template init lays into a new
repository, only when the repository has none (init_scaffold.py:889-904 never overwrites). From then on
scripts/verify.sh is the repository's own file: the template-sync check excepts it
(scripts/check_template_sync.sh:30, "every repository declares which checks it runs"), and this
repository's copy already differs from the template. So a change to the engine's gate script reaches
repositories initialized after it and no others. Existing projects are covered by VELDO-0325.

| Component | File | New or changed | Responsibility |
| :- | :- | :- | :- |
| Ledger | engine/.veldo/control_space.py | New | Owns the item, pool, hold, reconcile, event, mode, wrong-proposal and review group records in the control store. The only writer of them. Registers its commands and declares ownership of its entity kinds with the store's declare_owners, as control_andon.py:259 does |
| Declarations reader | engine/.veldo/control_space_config.py | New | Reads the installation's space section through the one installation reader, and each project's space file. Refuses a malformed one by name |
| Kind registry | engine/.veldo/control_space_kinds.py | New | Plain data and one pure function. For each kind: how an item is identified, its lifecycle table, which safety rules apply, which remover carries out each action |
| Probes | engine/.veldo/control_space_probe.py | New | The observers the safety rules read: process working directories, open and mapped files, container mounts, git state of a worktree and a branch, the protect list. Each returns facts; none decides |
| Process reader | engine/scripts/veldo_procread.c, added to the protected paths; installed by the owner at /usr/local/lib/veldo/veldo-procread | New | A static C program with the one file capability cap_sys_ptrace. Prints, for every process, the device and inode numbers of its working directory, open files and mapped files. Takes no input, attaches to nothing, signals nothing, writes nothing (7.1) |
| Removers | engine/.veldo/control_space_remove.py | New | One remover per action. Each uses the owning tool's own remove and reports what it measured |
| Signal | engine/.veldo/control_space_signal.py | New | The one entry point an emitting process calls with an event. Finds due items, runs rules and removers in line, writes the outcomes |
| Docker adapter | engine/.veldo/control_space_docker.py | New | Per engine context: the run label and compose project name, the snapshot, the event subscription, the census, the object removers |
| Reconciler | engine/.veldo/control_space_reconcile.py | New | Snapshot of roots and engines, comparison with the ledger, adoption rules, the report |
| Admission | engine/.veldo/control_space_admission.py | New | Pools, needs, holds, the mark that says a waiting hold may be judged again, the no-space classification |
| Event spool | engine/.veldo/control_space_spool.py | New | Keeps an event that a hook or the CLI could not deliver because the authority was not reachable, and replays it in order |
| Event consumer | engine/.veldo/control_space_consumer.py, called from the authority service | New | Takes the oldest event record a hook left and hands it to the space worker. It runs no git command and computes nothing |
| Space worker | engine/.veldo/control_space_worker.py | New | The child process the service starts for one event record. It works out what the event ends (for a landing, which recorded branches the new commit contains), then runs Signal. Its output pipe is in the service loop's poll set |
| Clone provisioner | engine/.veldo/control_clone.py | Changed | Declares the clone root, work tree and scratch folder before making them; teardown and failed-provision cleanup go through Signal |
| Fleet worktrees | engine/.veldo/fleet.py | Changed | Declares the worktree before git adds it; removal goes through Signal, without git's force option |
| Batch | engine/.veldo/control_batch.py | Changed | Declares the batch clone and the observation folder before making them (:530, :721); discard goes through Signal (:944-951) |
| Sandbox | engine/scripts/agent_sandbox.py, prepare, integrate and the launcher's scratch (protected, policy.yaml:22 and 35) | Changed | Declares the agent repository, the worktree and the branch before making them; integrate reports what it brought across. Under a recorded run it declares its scratch and leaves the removal to the run's event. Its pass that removed stale scratch by age is deleted |
| Gate leg timing | engine/scripts/gate_legs.py, prune_times (protected, policy.yaml:54-55) | Changed | Loses the branch that deletes a leg-time file for being older than 30 days. The 30-day value stays for the one reader that ignores an old measurement (6.10) |
| Settlement journey | engine/.veldo/control_request_settlement.py | Changed | Gains one request touchpoint, space disposition, whose three offered answers are picks. The set of rulings does not change (section 7) |
| Receiver | engine/.veldo/control_launch.py | Changed | Declares run folders (the run directory, artifacts, receipts, token records); sets the run's label and space environment; runs the census and sends run finished; classifies a no-space end. Its two direct removals of run directories go through Signal |
| Landing line | engine/.veldo/lander.py, control_launch_work.py | Changed | Candidate workspaces are declared as scratch and removed through Signal |
| Retirement | engine/.veldo/control_retirement.py | Changed | When a pending retirement's obligation completes and the retirement is carried out, the dispatch's deferred items are retried in the same call |
| Runner | engine/.veldo/control_launch.py, Runner.prepare | Changed | Asks Admission after its sweep and before it reserves anything; a wait leaves the unit waiting with no dispatch record |
| Dispatch contract | engine/.veldo/control_dispatch.py | Changed | The contract gains the field space (the hold and the needs) |
| Landing | engine/.veldo/control_landing.py and control_landing_station.py | Changed | After the completion receipt is recorded, sends landed for the unit |
| Gate script template | engine/scripts/verify.sh (protected, policy.yaml:83 and 86) | Changed | Calls the gate space helper at three points: before the first check, before the stamp, after the stamp. Reaches new repositories only |
| Each bound project's gate script | scripts/verify.sh in that project (protected there) | Changed, by that project's own spec | The same three calls at the same three points (VELDO-0325) |
| Gate space helper | engine/scripts/gate_space.py, added to the protected paths | New | The gate's need check, the no-space classification and the verdict recorded event. Read from the authority checkout, never from the candidate, as gate_host.py is |
| Authority service | engine/.veldo/control_service.py | Changed | At start: replay the spool, snapshot, subscribe, reconcile. After a packet that advanced the journal it runs the event consumer. Sends ticket ended and project ended after it commits those transitions. Gains the wake source space, raised only by a ledger write that frees space. The Docker event streams and the space worker's pipe are in its poll set |
| Git hooks | engine/hooks/post-checkout and engine/hooks/reference-transaction, installed into each bound repository | New | Record a worktree made by any git command (owned by the run when it is made detached inside a wrapped run) and a branch switch inside a recorded worktree, and record a change of the trunk or a landing ref. They record and return; they remove nothing |
| Session hooks | packs/claude/hooks/hooks.json and packs/claude/scripts | Changed | SessionStart records the session and its scratch; SessionEnd records that it ended. They record and return; they remove nothing |
| Host principals | engine/.veldo/control_service.py (the install), engine/bin/veldo | Changed | Two new host principals with their own keys: one for hooks, one for the gate helper and the run wrapper (6.11) |
| API | engine/.veldo/control_api.py and engine/ui/src/api/routes.json | Changed | The space reads and the owner actions of section 6.6 |
| Console | engine/ui/src/features/space, engine/ui/src/views/SpaceView.vue, engine/ui/src/app/navigation.ts | New and changed | The Space screen, the run view's space panel, the wait reason on the runs list |
| CLI | engine/bin/veldo | Changed | The verb space with status, reconcile, record, event, admit, run, covers, gate-check, reject and mode |
| Boundary check | scripts/check_space_boundary.py, called from scripts/verify.sh (protected, policy.yaml:83) | New | Refuses a creation primitive outside the ledger's seam, a removal primitive outside the removers, and any delete decided by a file's age or the clock |
| Scaffold | engine/.veldo/init_scaffold.py | Changed | Lays .veldo/space.yaml in a new project |

### Component view

```
  PROCESSES THAT REMOVE AT THEIR OWN EVENT          THE SPACE LIBRARY (runs inside the remover)

  Receiver (one per dispatch)     - run finished -+
  Run wrapper (CLI, outside run)  - run finished -+
  Gate script (a gate with the    - verdict  - - -+     +=============================+
    space steps)                                  +- -> | Signal                      |
  Landing station                 - landed  - - - +     |  1 ledger: which items due  |
  Space worker (child of the      - contained,    +     |  2 kind registry: action    |
    authority service)              session ended,      |  3 probes: facts            |
                                    ticket ended,       |  4 rules: remove or defer   |
                                    project ended,      |  5 remover: owning tool     |
                                    abandoned,          |  6 ledger: outcome          |
                                    released            +==============+==============+
  HOOKS THAT ONLY RECORD                                               |
  Git ref hook     - landing event record - +                          |
  Session hooks    - session started,       +- > journal advance       |
                     session ended records  |    wakes the event       |
  Host scripts     - released record  - - - +    consumer, which       |
                                                 starts the worker     |
                                                                       |
  CREATORS                                                             |
  Clones, Fleet, Batch, Sandbox,    - declare, - - - - - - - - - - - > |
  Receiver, Docker adapter, git       confirm                          |
  checkout hook, session start                                         |
  hook, run wrapper                                                    |
                                                                       |
  Runner.prepare, gate script, run wrapper - admit - > Admission - - > |
                                                                       v
  Authority service at start     - - - - - - -> Reconciler - > +===========+     +================+
  Console action, CLI                                          |  Ledger   | - > | Control store  |
                                                               +===========+     | (journal)      |
  Console (reads only, through the API)  <- - - - - - - - - - - - - - - - - - -  +================+
```

The library is not a daemon. It has no loop and no clock. It runs when a process calls it with an event
or a creation, and returns. The event consumer is not a loop either: it is one function the service calls
after a packet has advanced the journal, the same moment the service already uses to wake the factory
loop (control_service.py:1588-1596).

## 4. Data model

All records are entities of the control store, written only by the Ledger's registered commands, each
write one journal record. No second database.

### 4.1 Item

Identity: space:item: followed by a new identifier. One record per thing.

| Field | Content |
| :- | :- |
| kind | One of the ten kinds |
| host | The host the thing is on |
| pool | The pool its bytes count against |
| locator | For a disk kind: the absolute path. For a branch: repository and ref name. For a Docker kind: engine context, object id and name |
| parent | The item this one lives inside, when there is one (a build folder's worktree, a worktree's agent repository) |
| owner | scope: one of project, plain repository, or no project (always exactly one of the three), with the project's or repository's identity for the first two. Then ticket, run, gate, lane and session where they apply. A run is recorded with its station. No project is accepted only for the kind scratch with a session |
| creator | The component that declared it: a seam, a hook, the CLI's record verb, the run wrapper, census, or reconcile |
| adopted | True when reconcile created the record for a thing that already existed |
| branch | For a worktree: the branch checked out in it, or none when detached. Updated when the branch is switched (6.9) |
| start | For a branch and a worktree: the start commit. For an adopted one, the first entry of the branch's own log; absent when the branch has no log. An item with no start commit is never contained (section 5) |
| process | For a session's item: the session's process id and its start time, as the kernel reports them |
| state | declared, present, due, deferred, removing, removed, gone, kept |
| ends_on | The events of section 5 that apply to this item, copied from the kind registry at declaration with the registry's version |
| size | Bytes at the last measurement and the event it was measured at |
| confirmed | For an item made due in report mode: the owner's Confirm command that covered it. It stands until the item is removed or the owner marks it wrong |
| deferral | The rule that refused, the event it was refused at, the event that retries it, the number of attempts, and the decision request when one was raised, or the review group when the item is in one |
| removal | The event, the emitting process, the method, bytes just before, pool free before and after, and for an engine pool the host figure apart |
| report | For an item reconcile could not give an owner: what was found, why no rule adopted it, and the owner a rule proposes when one does |

States and the moves between them:

```
  declare           confirm            ending event            rules pass          remover done
 (nothing) -> declared -> present - - - - - - - - - -> due - - - - - -> removing - - - - - -> removed
                 |           |                          |  ^
                 |           | found missing            |  | next event
                 v           v                          v  |
               gone        gone                       deferred

  kept: a present item whose table action at its last event is keep (a branch, an evidence folder), or
        a worktree the owner answered keep for
```

A thing someone removed by hand has an item and nothing at its locator. The next event that reaches the
item marks it gone; so does reconcile.

A crash can leave an item declared with nothing on disk, or removing with a half-removed folder. Both are
finished by the next reconcile: a declared item with nothing there becomes gone, and a removing item is
removed to the end, because the decision to remove it was already made and recorded.

### 4.2 Pool

Identity: space:pool: followed by host and name.

| Field | Content |
| :- | :- |
| type | filesystem, or engine image |
| device | For a filesystem: its device identity, so two paths on one filesystem are one pool |
| engine | For an engine image: the context name |
| floor | Bytes that must stay free |
| returns_space | False for an engine image: removal inside it does not grow the host's free space |
| backing | For an engine image: the filesystem pool its image file is on |

A container engine whose data root is a folder on a filesystem is not a pool of its own. Its objects count
against that filesystem's pool. An engine that keeps its data in a disk image is its own pool, and its free
space is read from the engine. On the measured host that gives two pools: the one filesystem (which also
holds the system engine's data), and the desktop engine's image.

### 4.3 Hold

Identity: space:hold: followed by unit, station and attempt for a dispatch, or the gate run or wrapped
run identity. It exists before the dispatch does, because admission is asked before a dispatch is
prepared.

| Field | Content |
| :- | :- |
| needs | Per pool, the bytes the run declared |
| source | declared, measured, or default, per pool |
| state | waiting, advised, admitted, released |
| reason | For waiting and advised: pool, need, free, held by others, floor, as numbers |
| used | Per pool, the measured size of the run's own items at its last event |
| retry asked | True once the hold's one admission requested event has been sent (6.7) |
| freed | Set by the Ledger when it commits a write that frees space on one of the hold's pools; cleared when the hold is judged again (6.7) |

Advised is the report-mode outcome: the run would have waited, it was started anyway, and the numbers are
kept. An advised hold still counts as held, so a run of a project in act mode on the same pool is judged
against it.

### 4.4 Reconcile record

Identity: space:reconcile: followed by a new identifier. It holds what started it (service start, console,
CLI), the roots and engines read, and the counts: matched, adopted, reported, gone, completed. The findings
themselves are item records.

### 4.5 Event record

Identity: space:event: followed by a new identifier. One record per event a hook reported. A hook cannot
remove anything, so what it saw has to be a record the service can act on.

| Field | Content |
| :- | :- |
| type | ref changed, session started, session ended, or released |
| subject | For ref changed: the repository, the ref name, the old commit and the new commit. For the session events: the session id, its working folder, its process id and process start time. For released: the locators of the things the sending script made and is giving up |
| emitter | The hook, and the host it ran on |
| state | received, consumed |
| result | Written when consumed: the items the event made due, or "none" |

The record is written by the Ledger's event command. Writing it advances the journal, and that advance is
what wakes the consumer (6.9). A record is consumed once; a consumer that finds it already consumed does
nothing.

### 4.6 Spooled event

Not a store record. One file per event in a spool folder under the state root, written whole and then
renamed into place, holding what the event record would hold. The spool exists because a git hook must
never fail or wait on a service that is down. Section 6.9 says when it is written and replayed.

### 4.7 Mode record

Identity: space:mode: followed by the scope. One record per project, per plain repository, and one for
no project. A scope with no record is in report mode. The record is in the installation's store and not
in the project's repository, so a project cannot promote itself.

| Field | Content |
| :- | :- |
| scope | The project, the plain repository, or no project |
| mode | report or act |
| since | When the current mode began, and the owner's signed command that set it |
| history | Each earlier switch: from, to, when, the command, and for a switch to act what was checked: the three days that were counted, that no pending group was unconfirmed, and for a bound project that its gate script had the space steps |

### 4.8 Wrong-proposal record

Identity: space:wrong: followed by a new identifier. One record each time the owner marks a proposal
wrong.

| Field | Content |
| :- | :- |
| scope | The scope the proposal belonged to |
| proposal | One of: item made due, adoption, proposed Docker owner |
| subject | The item or the report it was about, and the event or the adoption rule that produced it |
| reason | The owner's words |
| day | The calendar day of the mark, in the installation's time zone |

What the mark does to the thing. A due item goes to kept, and nothing proposes it again until the owner
presses Abandon. An adoption is undone: the record loses its owner and becomes a report, and the owner can
give it another owner with Adopt. A proposed Docker owner is dropped from the report and that rule does
not propose it for that object again.

### 4.9 Review group record

Identity: space:group: followed by the scope, a calendar day and a sequence number, 1 for the day's
first group. A record is written when a review worktree is deferred for unique work other than review
scratch and its scope has no open group for that day (section 7). A scope has at most one open group per
day. A closed group is never reopened and never added to.

| Field | Content |
| :- | :- |
| day | The calendar day of the deferral event that opened the group, in the installation's time zone |
| sequence | The group's number within its scope and day, counted from 1 |
| members | The worktree items in the group. Each has a short index (1, 2, 3) in the order it joined, the review run that owned it, the list of files the owner is shown for it and, for a detached worktree with commits no ref holds, the name of the kept branch they go to (6.5). A member answered by a member pick has left the group and is recorded with that answer |
| request | The group's current decision request and its version. A member pick settles that request; the Ledger raises a new one for the members left and writes it here |
| state | open, closed. A group closes when a group pick is applied, or when its last member leaves by a member pick |

## 5. Kinds and lifecycle

One table, held in the kind registry as data. "Remove" always means: through the safety rules of section
7, by the remover of section 6.5. An empty cell means the event does nothing to that kind.

| Kind | Run finished | Verdict recorded | Landed or contained | Ticket ended or project ended | Worktree abandoned |
| :- | :- | :- | :- | :- | :- |
| Scratch | Remove | Remove | Remove | Remove | Remove |
| Build output | Remove, unless the same ticket has a queued run on the same worktree; then ownership passes to that run | Remove | Remove | Remove | Remove |
| Container | Stop, then remove | Stop, then remove | Remove | Remove | Remove |
| Network | Remove, after its containers | Remove | Remove | Remove | Remove |
| Volume | Remove, after its containers | Remove | Remove | Remove | Remove |
| Image tag | | | Remove the tag | Remove the tag | |
| Evidence | Measure | Drop caches inside it; keep the rest | Keep | Remove only the files whose digest the store or the landed commit already holds; keep the rest | Keep |
| Worktree | Measure | | Remove with git's non-forced worktree remove, after its build output | Remove the same way; a worktree with unique work is deferred and raises one decision request (section 7) | The same |
| Worktree owned by a review run (a review worktree) | Remove its review scratch, then remove with git's non-forced worktree remove, after its build output. One with any other unique work is deferred and joins the day's grouped decision request (section 7) | | Remove the same way | The same | The same |
| Worktree owned by a run of another station | Remove with git's non-forced worktree remove, after its build output; one with unique work is deferred and raises one decision request | | Remove the same way | The same | The same |
| Agent repository | | | Remove, after its worktree, once every branch in it is in the shared repository | The same; otherwise deferred as unique work | The same |
| Branch | | | Mark contained; keep | Keep | Keep |

Two more events. Session ended removes the scratch a session owns. Released by its creator has the
actions of the worktree abandoned column for every kind; it differs only in who may send it (below and
6.11).

A worktree owned by a run is one that was added detached inside a run (6.9). It has no branch to follow
and no ticket, so without these two rows it would end on nothing its run does. The usual case is a
review's throwaway checkout, and every review would leave one behind. The run's station says which row
applies. A review worktree is a read-only checkout, so what a review leaves in it is treated differently
from what a builder leaves (section 7).

The events, the existing thing that makes each true, and who emits it:

| Event | It has happened when | Emitted by |
| :- | :- | :- |
| Run finished | The dispatch record is conclusive and the kernel says its containment group is empty (the VELDO-0041 conditions). For a wrapped run: the command and its containment group have ended | The receiver of that dispatch; the run wrapper |
| Verdict recorded | A gate's stamp is written, or a review's verdict is recorded | The gate script through the gate space helper; the review's receiver |
| Landed | The VELDO-0057 completion receipt for the unit is recorded | The landing station |
| Contained | A branch has moved past its start commit, and its tip is reachable from the trunk, from a landing ref the project declares, from the source commit of a completed landing, or from another recorded branch | The event consumer, for a ref changed record whose ref is the trunk or a declared landing ref; the landing station at each landing; reconcile |
| Ticket ended | The authority commits one of four existing transitions: the backlog item's complete (ACTIVE to DONE) or cancel, the unit's dispose_unit (to CANCELED) (control_backlog.py:71-80, 178), or the assignment's dispose with the ruling close, the VELDO-0133 close (control_assignment.py:122, 529) | The authority service, after the command commits |
| Project ended | The authority commits the project's cancel or complete (control_project.py:141, 758) | The authority service, after the command commits |
| Worktree abandoned | The ticket's next run is provisioned in another worktree, or the owner presses Abandon on the console | The provisioner, or the API action |
| Released by its creator | A released record is consumed. A script outside Veldo sends it for a worktree or an agent repository it made itself and no longer wants. It is accepted only for items whose recorded creator is a hook or the CLI's record verb, never for an item a Veldo seam declared | The event consumer, for the record the script's CLI call left |
| Session ended | A session ended record is consumed; or a session started record is consumed and the kernel no longer shows the recorded process of an earlier session on the host | The event consumer |

Every transition in this table exists in the code today. There is no "superseded" transition in the
authority, so there is no event of that name, and this design adds no transition. If one is added later,
mapping it to ticket ended is one row in this table and its own ticket.

Who computes contained against what. The ref hook reports only changes of the trunk and of declared
landing refs, so the consumer tests recorded branches against those refs alone. "Contained in another
recorded branch" is computed by the landing station at a landing and by reconcile, and by nothing else: a
commit on an ordinary branch fires no contained event.

Three rules complete the table.

A worktree is never removed while an item inside it is there in any state but removed or gone: declared,
present, due, deferred, removing or kept. So the build output goes first, a deferred build folder holds
its worktree, and kept evidence or a kept worktree holds what it is inside (section 7, "A child holds its
parent"). An agent repository waits for its worktree in the same way.

An item that has no ticket (a gate on a batch, a worktree on a branch no pattern maps to a ticket, a
worktree in a plain repository) ends on its run's or its gate's events, on contained, on project ended and
on Abandon.

A branch that has not moved past its start commit is never contained. A worktree made a minute ago sits on
a branch whose tip is the trunk's tip; without this rule the next landing would remove it.

An item with no start commit is never contained either. That is an adopted worktree whose branch has no
log, and a detached one. It ends on landed, on project ended and on Abandon, and a detached worktree that
a run owns also ends at that run's run finished.

A worktree follows the branch that is checked out in it now. When someone switches a recorded worktree
from branch X to branch Y, the item's branch becomes Y and its start commit becomes the commit Y pointed
at when it was switched to. A later landing that contains X then marks the branch X contained and leaves
the worktree alone.

"Worktree abandoned" is an event, not an age. A worktree nobody has touched for a month is not abandoned
until one of the two things in the table happens. No row of this table, and nothing else in Veldo, removes
a thing because of how old it is. That holds with a central installation and without one.

The cost of removing build output at run finished: when no run is queued for the ticket, the next run on
that worktree rebuilds from nothing. The hand-over covers a queued run only. That is the owner's order of
priorities: space first, rebuild time second.

## 6. Interfaces

### 6.1 Ledger commands

Each is a registered command of the control store, journaled and signed like every other.

| Command | Input | Effect | Refuses |
| :- | :- | :- | :- |
| declare | kind, host, locator, owner, creator, parent, start | Creates an item in state declared, with pool and ends_on filled in | A locator on the protect list; a locator outside every known root; a second live item with the same locator |
| confirm | item | declared to present | An item not in state declared |
| measure | item, bytes, event | Writes size | |
| signal | event, subject | Marks every present, kept or deferred item whose owner matches the subject and whose table has an action at this event as due; returns them in removal order | An unknown event |
| outcome | item, one of removed, deferred, kept, with the facts | Writes the state and the removal or deferral fields | An item not due or removing |
| adopt | what reconcile found, the rule that proved the owner | Creates an item in state present with adopted true | The same refusals as declare |
| report | what reconcile found, and a proposed owner when a rule gives one | Creates or refreshes a report record; never an owner | |
| gone | item | present, declared, due or deferred to gone | |
| rebranch | worktree item, new branch, new start commit | Writes the item's branch and start; declares a branch item for the new branch when it has none | An item that is not a worktree, or is not present, kept or deferred |
| event | type, subject, emitter | Creates an event record in state received | An unknown type; a ref changed event for a repository that is neither bound nor plain; a released event that names an item a Veldo seam declared, or no item |
| consumed | event record, result | received to consumed | A record already consumed |
| reject | an item that is due, an adopted item, or a report with a proposed owner; the owner's reason | Writes a wrong-proposal record and applies its effect (4.8) | A command not signed by the owner; a subject that is none of the three |
| confirm group | scope, kind | Writes confirmed on every due item of that group the owner has not marked wrong, and hands the group to the space worker, which runs Signal for it | A command not signed by the owner; a scope in act mode |
| mode | scope, new mode | Writes the mode record and its history | A command not signed by the owner. For a switch to act: a scope whose last three calendar days were not each a clean report day, or with a wrong-proposal record dated today; a scope with an unconfirmed pending group; a bound project whose gate script lacks a space step. The refusal names the day that failed and why, each open group by scope and kind with its count, and each missing gate call |
| hold, admit, release | See 6.7 | | |

A switch back to report is always accepted. The three days, the pending groups and the gate script are
read at the moment the owner sends the command. Nothing counts them down and nothing switches a mode by
itself, so the rule is not a timer.

An unconfirmed pending group, exactly. It is a group of due items of the scope, of one kind, in which at
least one item has no confirmation and no wrong mark. A confirmed item that a rule then deferred is not
unconfirmed: the owner answered it, the confirmation stands, and the item's next event retries it without
a second Confirm. An item the owner marked wrong is kept and is in no group. So before the switch every
due item of the scope has been confirmed or marked wrong.

Open adoptions and proposed Docker owners do not block the switch. The lead's decision (d) names pending
groups. Those two kinds of proposal remove nothing by themselves, they stay under Reports, and the owner
can still mark each one wrong, which costs the scope a clean day.

The gate. For a bound project the Ledger also runs the gate check of 8.2 on the project's gate script as
its trunk holds it, and refuses act while one of the three calls is missing or misplaced. A plain
repository and no project have no gate and are not asked.

Known roots are the roots the declarations name: each project's and plain repository's worktree root, the
state root, the scratch roots and the build roots. Declare therefore depends on the declarations reader
and on the pool's device identity.

A creator inside Veldo that cannot reach the authority refuses its own creation as
unavailable_service:space_ledger. A hook or wrapper outside Veldo never refuses the command it rides on;
it spools the record (6.9). A repository with no central installation has no ledger; there every seam,
hook and helper stands down and things are created as today.

### 6.2 The seam a creator calls

Two calls around the creation: declare before, confirm after. If the creation fails, the creator calls
gone. The seam returns the item's identity, which the creator stores beside whatever record it already
keeps (the clone manifest, the dispatch record), so a teardown can name the item.

The boundary check keeps both sets complete. It reads Veldo's own code for the creation primitives (git's
worktree add, a new temporary folder, a container, volume, network or image creation through the Docker
client) and refuses any that is not inside a function the seam's list names. It reads the same code for
removal primitives (a recursive folder delete, git's worktree remove, an engine remove, a shell recursive
remove) and refuses any outside the removers and the reviewed list of section 6.10. A new creator or a new
removal is a change to one of the lists, which a reviewer sees.

The check has one more rule, for removal by age. It refuses any function that deletes something (a folder,
a single file, or a call to a remover) and also reads a file's time fields or compares the clock with a
threshold. A search of the engine at the design commit finds two such functions, the two that 6.10 changes:
the sandbox's remove_stale_scratch and the gate's prune_times. After those changes it finds none, and the
rule has no reviewed list: nothing in Veldo may delete by age.

### 6.3 What a run is given, and the census

The receiver gives every run four things in its environment, each a path or a name the ledger already
holds. The run wrapper of 6.9 gives a wrapped run the same four.

| Given | What it is | Why |
| :- | :- | :- |
| A scratch root | The run's temporary folder, already declared as scratch | Everything a tool puts in the temporary folder lands in a recorded place |
| A build root | A folder for build output outside the worktree, already declared as build output, for projects that ask for one | Tools the project names are pointed at it through the variables the project declares |
| A space label | One string unique to the run | Section 6.4 |
| A compose project name | Derived from the label | Section 6.4 |

The census runs at each of the run's events (the end of each dispatch, run finished, and a gate's verdict
recorded), before Signal:

1. In the run's worktree, ask git for untracked paths, ignored ones included. Every ignored folder at any
   depth that git reports as a whole is a build output item, whatever its name. Ignored files that are
   not inside such a folder are left alone and not recorded. Untracked paths that git does not ignore are
   unique work: they are not recorded as items, and they protect the worktree (section 7).
2. Measure the scratch root, the build root, each build output found, and the worktree without them.
3. Ask the Docker adapter for the objects carrying the run's label or compose project name.
4. Declare what is new, confirm it, and write the sizes.

Why an ignored folder in a recorded worktree may be treated as build output: a worktree recorded when it
was made, by a seam or by the git hook, started as a clean checkout. Every untracked thing in it was made
after that, and the project's own ignore rules say which of those are not source. A project that keeps
something precious in an ignored folder names it in its keep list (6.8), and the census then leaves it
out. This reasoning does not hold for a worktree reconcile adopted, whose history Veldo did not see:
there, only folders matching the project's declared build output patterns are recorded, and nothing else.

### 6.4 Docker

A run's Docker objects are owned through mechanisms the tools themselves provide:

| Mechanism | Covers | How |
| :- | :- | :- |
| The compose project name in the run's environment | Everything a compose file creates: containers, networks, named volumes | Compose stamps its project name on each as a label |
| The run's label | Objects Veldo itself creates (the container provisioner), and objects a project's own scripts create when the project passes the label on | Applied at creation |
| Compose's working folder and configuration file labels | An object compose created from a file inside a recorded worktree | Compose stamps the folder it ran in and the files it read on each object. When either resolves inside a recorded worktree, the object belongs to that worktree |
| A bind mount's host source | A container that mounts a path inside a recorded worktree | The engine reports each mount's host source |

The last two rows are the adoption rule for objects that carry no run label. In report mode such an object
is a report with the proposed owner shown. In act mode it is adopted, with the worktree as its parent, and
the table applies. The builder checks on both engines that compose writes these labels before relying on
them, and records the result in the proof; an engine that does not write them simply gets no adoptions by
this rule.

An object with none of the four is not attributable. Two runs can share an engine, and the engine's event
for a new container does not say which process asked for it. The adapter records such an object as a
report, shows it on the console with the runs that were live on that engine when it appeared, and never
removes it in this release. The owner can assign it to a ticket with the Adopt action, after which the
table applies.

Per engine context the installation names, the adapter:

1. takes a snapshot at service start: containers, volumes, networks and images with their labels;
2. subscribes to the engine's event stream for as long as the service runs. The stream is the output
   pipe of one client process per engine, and that pipe is in the service loop's poll set beside the
   launch pipes and the provisioner pipes (control_service.py:1889-1895, 3490-3493). A readable pipe is
   an event; there is no thread and no timeout. Each create, start, stop and destroy event becomes a
   ledger write or a report;
3. on a broken stream (end of file on the pipe), takes a new snapshot and reconciles before it subscribes
   again.

Images. An image tag a run built is an item and is removed with its ticket. An image a run pulled is not
an item: it is recorded once per engine as kept, with no ending event, because nothing in Veldo can prove
it can be pulled again. The protect list names the images known not to be.

Order at an event. Containers are stopped and removed first, then networks, then volumes. A volume a
container still uses is deferred by the engine's own refusal.

### 6.5 Removers

| Action | Method | It refuses by itself when |
| :- | :- | :- |
| Remove a disk folder | Rename it to a marked name beside itself, run the in-use probe again on the new name, then delete it; if the second probe finds a user, rename it back and defer. Before the delete it opens up directories a confined process left unreadable or unwritable, through descriptors and without following a link, as the sandbox's own remove_tree does today (agent_sandbox.py:2052-2071) | The folder is a mount point, or is not on the item's pool |
| Remove a worktree | git's worktree remove, without the force option | git finds a modified tracked file or an untracked file |
| Remove an agent repository | The folder remover, after the unique work rule has compared its branches with the shared repository | |
| Remove an image tag | The engine's image remove, without the force option, on the tag | A container uses the image |
| Stop and remove a container | The engine's stop, then remove, without the force option | |
| Remove a volume | The engine's volume remove | A container uses the volume |
| Remove a network | The engine's network remove | An endpoint is attached |
| Drop caches in an evidence folder | Remove the sub-folders the project declares as caches; nothing else | |
| Mark a branch contained | A ledger write; git is not called | |
| Remove review scratch | For a review worktree only. Asks git for the worktree's untracked paths that it does not ignore and removes each one: a folder by the folder remover's rename, second probe and delete, a file by a plain delete, a link by deleting the link and never what it points at. Each path passes rules 1, 2, 3, 4 and 6 first. No force option and no clean command of git is used | A path resolves outside the worktree, is on the protect list, or is in use |
| Discard a worktree | git's worktree remove with the force option, on a worktree named by a settled owner decision: the one worktree of its request, each worktree of a review group, or the one member a member pick names. For a detached worktree whose checked-out commit no ref holds, the Ledger first creates a kept branch at that commit, and the remove runs only after that | The decision is not settled, does not name that worktree, the worktree's list of changed files differs from the list the owner was shown, or the kept branch could not be created |

No remover calls a prune command. No remover passes a force option, with the one exception in the last
row. Discard is the one forced removal, and it is allowed only after the owner's discard answer (section
7). Discard removes the worktree and never the branch, so work that was committed on a branch survives
it.

Discard never loses a commit (the lead's decision (g)). A detached worktree has no branch, so a commit
made in it can be reachable from no ref (rule 5, case 5). Before the discard remover runs on such a
worktree, the Ledger creates a kept branch at the commit checked out at that moment and records it as a
branch item in state kept. The branch is named as Save names one: the ticket's kept-branch name for a
ticket's worktree, otherwise the prefix space-saved, then the run's label. Every character of the label
that git refuses in a ref name is replaced by '-', and git checks the name before the write. Only then is
the worktree removed with the force option. What Discard loses is uncommitted work only: tracked edits,
staged changes and untracked files.

The order has one failure. When the branch cannot be created, because the name is taken by a branch
that does not hold the commit or because git refuses the ref, the discard does not run and the worktree
is deferred as remove_refused with everything in it. Discard never proceeds without the branch.

Creating the branch is a ref write. It is not a removal, so Discard stays the one forced removal. It is
not a commit, so "Veldo never commits on its own" still holds. git runs the reference-transaction hook
for it, and the hook sends nothing, because the ref is neither the trunk nor a declared landing ref
(6.9).

An agent's worktree needs no new branch. Its commits are on its branch in the agent repository, which
rule 5 keeps until the runner's integrate has brought them across. Discard of an agent's worktree
removes the worktree and leaves the agent repository and its branch in place, kept.

The review scratch remover is not a forced removal: it deletes, one by one, files that git
itself calls untracked, and the worktree then goes by the same non-forced remove as any other. Each
remover returns the bytes it measured just before, and the pool's free space before and after.

### 6.6 API and console actions

Reads, all from ledger records, live through the existing record stream:

| Route name | Returns |
| :- | :- |
| space.pools | Each pool: capacity, free, floor, held, and the waiting and advised holds with their numbers |
| space.usage | Bytes and item counts grouped by project, by ticket and by kind; filters for each. Plain repositories are rows beside the projects, and "no project" is a row of its own |
| space.pending | Due and deferred items: owner, kind, locator, size, reason, the event that retries it, and the decision request when there is one. The review worktrees of one group share one request, and each is shown with the index its member picks use |
| space.removed | Removed items, newest first: owner, kind, locator, event, emitter, size, free before and after |
| space.reports | What reconcile found and could not adopt, with the proposed owner when a rule gives one; repositories whose hooks are missing; bound projects whose gate script lacks the space steps |
| space.protected | The protect list in force, where each entry comes from, and the objects each entry matches on each engine. A protected thing appears here and in no other read |
| space.modes | Each scope's mode and since when; for a scope in report mode, the last three calendar days with what made each one clean or not, its wrong-proposal records, its unconfirmed pending groups by kind with their counts, and for a bound project whether its gate script has the space steps |

Owner actions, each a signed command through the API like every other owner action:

| Route name | Does |
| :- | :- |
| space.reconcile | Runs a reconcile now, for one project or all |
| space.adopt | Gives a reported thing an owner |
| space.abandon | Emits worktree abandoned for one worktree |
| space.confirm | Confirms one group of due items, a project and a kind, in report mode. Items the owner marked wrong are no longer in the group. The confirmation is written on each item and stands through a deferral |
| space.reject | Marks one proposal wrong, with the owner's reason: a due item, an adoption, or a proposed Docker owner |
| space.mode | Switches one scope to act, or back to report. The Ledger refuses act until the three clean report days are there, no pending group is unconfirmed and, for a bound project, the gate script has the space steps (6.1) |

The answers to a unique-work decision request are not new routes. They go through the existing request
settlement path (section 7).

### 6.7 Admission

| Call | When | Result |
| :- | :- | :- |
| hold | In Runner.prepare, after its sweep and before it reserves a slot (control_launch.py:810-817); in the gate script before its first check; in the run wrapper before it starts the command | Writes a hold in state waiting with the needs |
| admit | Straight after hold, and again whenever the unit is offered | Admitted, or waiting with the reason; in report mode, advised. For a hold that is already waiting, the answer is judged again only when its freed mark is set (below) |
| release | Run finished, after Signal; and when a prepared dispatch is refused | Hold released |

Why before prepare. A prepared dispatch holds its account slot and reservation, blocks another dispatch of
the same unit and station, and is refused once its deadline has passed (control_dispatch.py:134, 476-495,
520-521). A dispatch that waited an hour for space would die on its deadline while holding a slot. So the
question is asked before any of that exists. When the answer is wait, prepare refuses with
space_wait:<pool>, and no dispatch record, slot, reservation or deadline is made. The factory loop today
lists a refused offer as waiting only when the refusal starts with no_account; every other refusal goes
to its refused list (control_service.py:2640-2646). That branch changes: a refusal that starts with
space_wait joins the waiting list, with the numbers.

The dispatch contract gains one field, space, holding the hold's identity and the needs per pool. It joins
the contract's field list (control_dispatch.py:137-138), so it is covered by the contract digest of every
dispatch prepared from then on (VELDO-0039). A stored contract keeps the digest it was written with. At
acceptance in act mode the receiver's accept checks the hold is still admitted, as it re-reads the
reservation.

Where a need comes from, first that applies: the project's space file states it for the station; else,
once the project and station have five finished runs, the largest measured size of the last five; else the
pool's default need for the station from the installation. A gate's need is read from the project's space
file and not from gate_host.json, because most repositories have no gate_host.json.

The rule, per pool: free now, minus what admitted runs still hold, must be at least the need plus the
floor. What a run still holds is its need minus the size of its own items at its last measurement, never
below zero. Free now is read from the filesystem or the engine at the moment of the call.

The first time a hold would wait, and only then, admit runs Signal with the event admission requested for
the pool, which retries that pool's deferred items once. If that frees enough, the run is admitted. If
not, the hold moves to waiting with retry asked set, and no later admit call for that hold sends the
event again.

What judges a waiting hold again. Three ledger writes free space or change what is known about it: a
removal outcome with freed bytes on the pool, a hold on the pool released (a run ended), and a reconcile.
When the Ledger commits one of them it sets the freed mark on every waiting hold of that pool and raises
the factory loop's new wake source, space. Nothing else sets the mark.

The factory loop offers a waiting unit on every pass, and a pass runs on any wake: a journal advance, a
run's end, a working tree change and the account-reset timer (control_service.py:1595-1596, 2543, 3243,
3494-3496). So prepare calls admit for a waiting hold on passes that have nothing to do with space. On
such a call admit finds the freed mark clear and returns the recorded answer. It reads no free space, runs
no Signal and writes nothing. Only a call that finds the mark set reads the pool again, judges the hold
and clears the mark. A pass the account-reset timer woke therefore does nothing for a unit waiting for
space, and deferred items get their next try from their own events, never from the pace of the passes.

Space the owner frees by hand is not an event Veldo sees. It is taken into account at the next freeing
write on the pool, or at once with Reconcile on the console.

A waiting gate answers NOT STARTED with the reason and exit 75, the answer VELDO-0220 already has for a
held lock. A waiting wrapped run exits 75 with the same numbers and does not start its command. Neither
is queued by Veldo: each new start is a new hold and a new request.

Mode. Admission reads the mode of the scope the run belongs to: the project of the unit or the gated
repository, and for a wrapped run the project or plain repository its working folder is inside, else no
project. In report mode admission never blocks: it writes the hold as advised, shows "would wait" with
the numbers on the console and in the run's output, and the run starts. Admission blocks only in act
mode. Two projects on one pool can be in different modes; the pool's arithmetic is the same for both, and
only the answer differs.

### 6.8 Declarations

The installation's space section (the installation folder, read by the one installation reader). The
reader's rule is that nobody is a default (installation.py:23-26). So the section is optional as a whole:
an installation with no space section has space management off, the same as enabled false. When the
section is present, every key below is required and a missing one is refused by name as
installation_missing.

| Key | Content |
| :- | :- |
| enabled | Off stops every removal, every admission check and the no-space classification; the ledger stays readable |
| time zone | The zone whose calendar days the three-day rule counts |
| pools | Per pool: floor, and the default need per station |
| engines | The Docker contexts Veldo may read and act on |
| scratch roots | Folders outside projects where run and session scratch lives, and the pattern that gives a session's scratch folder from its session id and working folder |
| build roots | Folders outside worktrees where build output is kept under a worktree's name |
| plain repositories | Git repositories that do not run Veldo and whose worktrees are to be recorded, each with its worktree root |
| client accounts | The client configuration folders the session hooks are installed into |
| process reader | The word none, or the SHA-256 digest of the process reader the owner installed (7.1). The reader's path is fixed in the probe and is not a key |
| protect | Path prefixes; Docker name patterns for volumes, containers, images and networks; compose project names. Every entry applies on every engine the installation names. An object is protected by its name or by its compose project label, either one (section 7) |

Mode is not a key of this section. It is a ledger record per scope (4.7), written only by the owner's
signed command, so editing a file cannot put a project into act mode.

A project's .veldo/space.yaml, laid by init. This is the project's file, not the installation's, so it has
defaults:

| Key | Content | Default |
| :- | :- | :- |
| worktree root | Where the project's worktrees live | The folder beside the repository named after it with the suffix -worktrees |
| branch pattern | How a branch name gives a ticket | The agent branch patterns Veldo itself creates |
| landing refs | Refs besides the trunk whose change means work was landed | None |
| build output | Extra folder name patterns, for adopted worktrees and for folders git does not ignore | None |
| build variables | Environment variables to point at the run's build root | None |
| keep | Ignored paths the census must leave alone | None |
| evidence caches | Sub-folders of an evidence folder that are caches | None |
| needs | Per station (build, review, gate): bytes per pool | Measured after five runs, until then the pool default |
| protect | Additions to the installation's protect list | None |

A project may add protection. It cannot remove an installation entry.

A repository that is neither bound to the installation nor named as a plain repository is not read at
all. A plain repository gets the git hooks and the worktree, branch and build output kinds, with the
repository as the only owner; its worktrees end on contained and on Abandon. A plain repository is a scope
with a mode of its own, and goes to act by the same three-day rule.

### 6.9 Event sources outside the service

Each row is a mechanism that runs inside the process that creates or ends something. None is an
instruction an agent has to remember.

| Process | What it creates or ends | Mechanism | Why it cannot be skipped |
| :- | :- | :- | :- |
| Any git command that adds a worktree | A worktree and usually a branch | The post-checkout hook in the repository. git runs it at the end of worktree add, in the new worktree, with the null commit as the previous HEAD. It records the worktree and its branch as present, with the start commit and the owner the branch pattern gives | git runs the hook itself. The person or script typing the command does nothing extra |
| A script inside a wrapped run that adds a throwaway worktree (a review) | A detached worktree | The same post-checkout hook. A wrapped run has the run's space label in its environment, and the hook inherits it. When the label is there and the new worktree is detached, the hook records the worktree with that run as its owner, so it ends at the run's run finished. The Ledger reads the station from the run the label names; when it is review, the worktree is a review worktree (section 7). A worktree added on a branch inside a wrapped run keeps the owner its branch pattern gives | The same. The script does nothing extra, and its own forced remove goes away |
| A script outside Veldo that gives up a worktree or an agent repository it made | The end of those things | The CLI's event verb with the type released, in the place of the script's own recursive delete. It leaves one event record and returns. The consumer and the worker do the rest through all seven rules | The delete is gone from the script, so the call is the only way the things leave. Until the repository is in act mode the script keeps its delete (section 11) |
| Any git command that switches the branch of a recorded worktree | The worktree's branch | The same post-checkout hook. On a branch checkout (its flag is 1) with a previous HEAD that is not the null commit, inside a recorded worktree, it sends rebranch with the new branch and its commit | The same |
| Any git command that moves the trunk or a landing ref | Landed or contained | The reference-transaction hook. git runs it for every ref change; in its committed state the hook sends one event record for each changed trunk or declared landing ref (repository, ref, old commit, new commit) and returns. It computes nothing and removes nothing. The service's event consumer does the rest (below) | The same. A hand-made landing commit, a fast-forward and a fetch all pass through it |
| A gate whose script has the space steps | Build output, verdict | The gate script calls the gate space helper before its first check, before the stamp and after it (section 8.2). It does this with or without a gate_host.json | The steps are in the gate script that writes the stamp. A gate that skips them is not the gate |
| A gate whose script does not have the steps yet (every existing project until its own change, VELDO-0325) | Build output | The run wrapper around the gate command, in the host's gate launcher. It gives admission before the gate, and the census and run finished after it, which removes the build output. It cannot give NOT JUDGED, because the gate script has written its stamp by then | The launcher is the one place gates start on the host. Reconcile lists every bound project whose gate lacks the steps under space.reports, so an uncovered gate is visible and not silent |
| A lead session | Session scratch | The client's SessionStart and SessionEnd hooks, installed in every client account folder the installation names. Each sends one event record and returns | The client runs them. A crashed session is caught when the next session starts anywhere on the host |
| A builder or any heavy command started outside the receiver | Scratch, build output, containers | The run wrapper, the CLI's space run: hold and admit, declare the run with its station, scratch root, label and compose project name, start the command in its own containment group, then census, run finished and release | The host's launch scripts start their client through it (section 11). For a client that has session hooks, the hooks still record the run when someone bypasses the launch script |
| A command queued on the host lock | Whatever it builds | The same wrapper, placed inside the lock, so admission is judged when the command's turn comes and not when it joined the queue | The lock script is the one place such commands start |

The event consumer. A hook's packet reaches the authority over the existing local socket
(control_client.py). The Ledger's event command writes the event record, which advances the journal. The
service already acts on that advance: after a packet that advanced the journal it wakes the factory loop
with the source journal (control_service.py:1588-1596, and the loop's wake at :3227). The consumer is
called at the same place, and does not depend on a factory loop being configured. Event records in state
received are handled oldest first:

| Event record | What it makes due |
| :- | :- |
| ref changed, on the trunk or a declared landing ref | For each recorded branch of that repository that has a start commit and has moved past it, test whether its tip is reachable from the recorded new commit. For each that is, the worktree on that branch, its build output and its agent repository become due with the event contained. If the recorded new commit no longer exists, nothing is contained by this record |
| session started | For every session recorded on this host whose recorded process (id and start time) the kernel no longer shows, the session's scratch becomes due with session ended. This covers sessions of every project and of no project |
| session ended | That session's scratch becomes due with session ended |
| released | The named items become due with the event released by its creator |

The consumer itself does none of that work. It takes the oldest received record and starts the space
worker with it. The table is what the worker does: a repository with a hundred recorded branches needs a
hundred ancestry tests for one landing, and those must not run in the service loop. The worker then runs
Signal (rules, removers, outcomes) and marks the record consumed with the result. Its output pipe is in
the service
loop's poll set beside the launch pipes and the provisioner pipes (control_service.py:1889-1895,
3490-3493), so the service answers other packets while a large folder is being deleted. One worker runs
at a time. Records that arrive while it runs stay received and are taken, in order, when its pipe closes.
The authority service uses the same worker for the events it emits itself (ticket ended, project ended,
Abandon, a confirmed group), for the same reason.

This is an event and a subscription inside one process. Nothing reads a clock, nothing polls, and the
git command or the session never waits for a removal.

What each mechanism does when the authority is not reachable. A Veldo creator refuses its creation. A hook
or the wrapper must not fail the git command, session or build it rides on, so it writes the record or
event to the spool and returns. The spool is replayed, in order, the next time any CLI call or hook
reaches the authority, and at service start before reconcile. So removals that follow a hook need the
service running. Migration step 1 starts it; while it is down nothing is removed and nothing is lost.

Four limits, stated so nobody assumes more.

Veldo's own guarded git runs with the repository's hooks out of play. Some calls point the hooks folder
at nothing (candidate_git.py:74 and 83, agent_sandbox.py:772, and the host's sandbox script). The
transport commands point it at a private folder (git_process.py:144). Either way the installed hooks do
not run. Worktrees made that way are Veldo's own creations and are recorded by the seam of 6.2, not by the
hook.

A person can switch a repository's hooks off for one command, and git's worktree add with its no-checkout
option runs no post-checkout hook. That worktree is then found by the next reconcile and adopted.
Reconcile also reports a bound repository whose hooks are missing.

Loose files that a session's own commands write straight into the session scratch root, outside the
session's folder, have no provable owner. They stay reported, with their total size on the Reports
section, and Veldo never removes them. A wrapped run does not add to them: its temporary folder is its
own scratch root, and its log goes where the launch script puts it.

Removing a worktree by hand fires no hook. Nothing needs removing then; the item is marked gone at its
next event.

Hook installation. When a repository is bound, and for each plain repository the installation names, Veldo
puts the two hooks in the repository's shared hooks folder, which every linked worktree of it uses. Where a
hook file already exists, one marked line is added to it and the rest is left. Where the repository
configures its own hooks folder, the hooks go there. The hook starts the CLI with git's own environment
variables cleared, so nothing the CLI does is aimed by accident at the repository the hook fired in.

### 6.10 Existing removal paths

Every place in the engine that removes a folder or a worktree today, and every place that deletes
anything by age, and what happens to it. Line numbers are the engine canon at the design commit. The list
was made by searching the engine for the recursive folder delete, git's worktree remove and the shell's
recursive remove, and it was checked again against the second and third validations' lists. For removal
by age the search was for every function that both deletes and reads a file's time; it found two. The
boundary check of VELDO-0304 is what keeps the list complete from then on.

Replaced. After the change none of these calls a delete itself:

| Path today | What it does | Replacement |
| :- | :- | :- |
| fleet.py:149-155 | git's worktree remove with the force option; errors swallowed | Signal with worktree abandoned for the worktree's item. The worktree remover passes no force option. A refusal is a deferral on the record and on the console, never swallowed |
| control_clone.py:757-761 | Deletes the clone's work tree, scratch and root, ignoring errors, after the clone_in_use check | The clone_in_use refusal stays first, unchanged. Then Signal with run finished for the clone's items, through the folder remover. The pins are released only after the removal outcome is written |
| control_clone.py:606 | Deletes the clone root when provisioning fails | The declared items go through the folder remover and are then marked gone |
| control_launch.py:762-787, clear_runs, called from Runner.sweep at :714-722 | Deletes the run directory of each leftover dispatch whose run the kernel shows gone | The run directory (under runs_root, control_launch.py:538-542) is a scratch item owned by its dispatch. clear_runs calls Signal with run finished for the leftover; its kernel test is rule 3 |
| control_launch.py:1389-1397, _remove_run | The receiver deletes its run directory before it reports its end | The same item, removed by the receiver's Signal at run finished |
| control_launch_work.py:105-107 | Deletes the landing line's candidate folders at close | Candidate folders are scratch items; removed through Signal at close |
| lander.py:534-541, discard | Deletes the candidate workspace and observation folder | The same |
| control_batch.py:944-951, discard | Deletes the batch clone (made at :530 under the workspace root) and its observation folder (made at :721), ignoring errors | Both are declared as scratch items owned by the batch's project and gate before they are made. discard calls Signal with run finished for the batch's items; a refusal is a deferral, not an ignored error |
| engine/scripts/agent_sandbox.py:2223, the launcher's own scratch at the end of a run, through remove_tree at :2052-2071 | Deletes the scratch folder the launcher made at :2207 | Under a recorded run (the run's space label is in the environment) the launcher declares its scratch as a child of the run's scratch root and removes nothing; the run's run finished removes it through the rules. Rule 4 counts a held scratch lock and an unsettled borrowed login (VELDO-0211) as use, so the copy the launcher keeps today is still kept. With no space environment the launcher still removes its own scratch at its own end, which is an event; that call is on the reviewed list |
| engine/scripts/agent_sandbox.py:2074-2110, remove_stale_scratch (the age test at :2095 against STALE_SECONDS, 24 hours, at :2047), called at :2202 | Deletes scratch folders of killed launchers that are untouched for more than a day and whose lock is free. This is a removal by age | Deleted, with its call and its constant, in every case. Under a recorded run a killed launcher's scratch is an item of its run and goes at that run's run finished, or at reconcile when the run is over. With no installation, or outside a recorded run, a killed launcher's scratch stays until the owner removes it; with an installation reconcile lists it under Reports. The recovery of borrowed logins that runs before it (recover_orphans, :2201) is unchanged |
| engine/scripts/gate_legs.py:267-299, prune_times, called at :205 and :264 | Deletes a leg-time file from the gate's timing store (os.unlink at :292) when the file is older than STORE_MAX_AGE_DAYS, 30 days (:107), or when the authority checkout the file names no longer exists | The age branch is deleted: prune_times no longer reads a file's time or the clock. The other branch stays: it is a test made at the moment a gate writes its own timing, on a fact (the checkout is gone), and it removes a small timing file that nothing can read again. The constant is not deleted, because read_resources at :236 uses it too: it ignores a resource measurement older than 30 days and answers as if there were none. That is a read, it deletes nothing, and decision (c) does not reach it; the constant is renamed to say it bounds a read. prune_times also stops touching the store's .pending- files (:279), which it removed by age alone. They carry no authority field, so no fact is left to remove them on, and a partly written file a killed gate left stays. The module text at :70-72, the function's own description and the line it prints (:297-298), which all state the age rule, are corrected. A single-file delete is not one of the boundary check's removal primitives, so the function needs no reviewed-list entry; the check's age rule is what it must pass. The file is protected (policy.yaml:54-55), so the change is its own ticket, VELDO-0333 |

Stay, on the boundary check's reviewed list. Each makes a folder with a fresh temporary name, hands it to
nobody outside the call, and removes it before the call returns or as one step of an install that replaces
a folder it has just built. None can hold a worktree, build output or another run's files:
control_repository_provisioner.py:241, fix_validation.py:672, control_memory_check.py:133, 149 and 230,
control_graph.py:602-607, control_graph_install.py:83-86 and 116, init_scaffold.py:835-849,
engine/scripts/agent_sandbox.py:1846 (a borrow journal), 2041 (a recovery folder after its content is
restored) and 2759 (the self-test's own worktree), engine/scripts/runners/process/process_runner.py:351,
engine/scripts/runners/plugin/plugin_load_runner.py:308-309 (the plugin load check's two temporary
folders), engine/scripts/check_gate_mutations.py:814 and 1115,
engine/scripts/gate_schedule.py:436, and the gate script's own schedule folder (engine/scripts/verify.sh:160-163).

Four more entries stay for a different reason, each named with it:

| Path | Why it stays |
| :- | :- |
| control_service.py:894-898, _remove_tree, called at :1006 | Rolls back a failed install of the service: it removes only the folders that same install call created |
| control_service.py:894-898, _remove_tree, called at :1204 | Removes the service's own home at uninstall, on the owner's uninstall command. The ledger lives in that service; it cannot remove its own host through itself |
| engine/scripts/agent_sandbox.py:2223, through remove_tree at :2052-2071 | Runs only when no space environment is present: the launcher removes the scratch it made, at its own end. Under a recorded run the row above applies |
| engine/scripts/mutation_ownership.py, cleanup, at :286 and :288 through remove_tree at :200 | Removes only the directories that one mutation test worker recorded in its own ownership ledger, when the coordinator ends that worker. That is an event, and the list is the worker's own |

The list names each function and its reason. A removal primitive anywhere else fails the gate.

Outside the repository, on the measured host (provenance; changed when the installation is set up, section
11):

| Path today | What it does | Replacement |
| :- | :- | :- |
| myday/scripts/nightly_build_cleanup.sh:92, on the user schedule | Recursive delete by age | Retired by the check of section 11. Until then it asks the ledger and skips what the ledger says to keep. While it runs it is the one thing on the host that removes by age. It is outside Veldo, and section 11 bounds how long it lives |
| myday/scripts/gate_core_cand.sh:41 | Deletes the worktree's build folder after every gate | Kept while core is in report mode, because in report mode Signal removes nothing. Removed when core is in act mode (section 11, step 9). By then core's own gate script has the space steps, and the gate's verdict recorded removes the build folder through the rules |
| myday/scripts/gate_core_cand.sh:32-37 | Refuses a gate under 60 GB free | Kept while core is in report mode, because there admission only advises. Removed in the same step |
| myday/scripts/codex_review.sh:51 | Forced worktree remove of the review worktree at exit (the worktree is added detached at :55) | Kept while core is in report mode. Removed in the same step: the worktree is owned by the wrapped review run (6.9), and the wrapper's run finished removes its review scratch and then the worktree, by git's non-forced remove, after its build output |
| myday/scripts/agent_sandbox.sh:246 | Recursive delete of the half-made worktree and private repository when the script's own prepare fails | Replaced by the CLI's event verb with the type released, signed as space-observer, for the two things the script recorded. Kept while the repository is in report mode |
| myday/scripts/agent_sandbox.sh:476 | Recursive delete of an agent worktree and its private repository in the script's remove command, after its own check that the agent's branch is in the shared repository, or with its force flag | The same released event. The script's check and its force flag go: rule 5 compares the agent repository with the shared one, and a refusal is a deferral with one decision request, never a forced delete. Kept while the repository is in report mode |

### 6.11 Who signs a space command

A command to the authority needs two things: a peer the kernel vouches for, and a signature the authority
can verify (control_client.py:10-23). The CLI's existing commands are signed by the owner's enrolled key.
A git hook runs in any shell and must not hold that key. The service and the receiver already have host
principals of their own, authority and launch-receiver (control_service.py:951-952). This design adds two
more, each with its own key made at install and kept in the installation folder.

| Principal | Used by | Commands it may sign | Refused |
| :- | :- | :- | :- |
| space-observer | The git hooks, the session hooks, and a host script through the CLI's record and event verbs | declare and confirm for a worktree, a branch, an agent repository and session scratch; rebranch; event, with released accepted only for items a hook or the record verb declared; the read behind covers | Everything else |
| space-runner | The gate space helper and the run wrapper | What space-observer may, and for the run or gate it started: declare, confirm, measure, hold, admit, release, signal and outcome | Every owner action |
| launch-receiver (exists) | The receiver | The same run commands, for its own dispatch | As today |
| authority (exists) | The service, the event consumer, the space worker, reconcile | Every ledger command | |
| The owner | Console and CLI | Adopt, Abandon, Confirm, Reconcile, marking a proposal wrong, the mode switch, changes to the protect list, and the answers to a decision request | |

An observation can make something due; it can never stand in for an owner's answer. Discard, Save and Keep
are accepted only as a settled request signed by the owner.

Released is not Abandon. Abandon is the owner giving up any worktree. Released is a script giving up
something that same script made outside Veldo, and the Ledger refuses it for anything else. Both go
through all seven rules, so neither can remove unique work.

## 7. Safety rules

Every removal passes these, in this order, and the first that refuses names the deferral. The rules read
the probes' facts at the moment of the attempt; no fact is carried over from an earlier attempt.

| Order | Rule | Refuses when | Deferral |
| :- | :- | :- | :- |
| 1 | Ledger | The thing at the locator is not the item recorded (another object id, another repository, a path that now resolves elsewhere through a link) | not_in_ledger |
| 2 | Protect | The locator, or anything beneath it, matches the protect list | protected |
| 3 | Owner live | The item's owning run is not conclusive, or its containment group is not empty; or the owning session's recorded process is still the same live process | in_use |
| 4 | Process use | Any process has its working directory, an open file or a mapped file at or beneath the path; or a container on any named engine, running or stopped, has a bind mount at or beneath it; or git holds a lock on the worktree; or, for a sandbox launcher's scratch, its scratch lock is held or its borrowed login is not settled; or any of these could not be read and could hold the path (below, "What a probe cannot read") | in_use |
| 5 | Unique work | See below. Unique work that could not be read is unique work | unique_work |
| 6 | Children | An item inside this one is in any state but removed or gone (declared, present, due, deferred, removing or kept); or something on disk inside it is not recorded, or its inside cannot be read (below, "A child holds its parent") | in_use |
| 7 | Tool | The owning tool's non-forced remove refuses | remove_refused |

Rule 5, unique work. For a worktree it refuses in any of these cases:

1. a tracked file is modified;
2. a change is staged;
3. an untracked file exists that git does not ignore;
4. an operation is in progress (a merge, a rebase, a cherry-pick);
5. a commit on the worktree's branch is reachable from no ref other than that branch itself, from no
   completed landing's source commit and not from the trunk. The test covers every commit on the branch.
   The branch tip is the checked-out commit, so testing the tip against the other refs is enough, but the
   rule is about the branch and not about what happens to be checked out. A detached worktree is tested
   on its checked-out commit against every ref. A ref here is a branch, a tag or a remote-tracking ref.
   A stash is not one: the stash entry made in a worktree has the checked-out commit as its parent, so
   git lists refs/stash among the refs that reach it, and once the worktree is removed and the stash
   dropped the commit is lost. Git's per-worktree refs do not count either.

Case 3 has one exception, by name: review scratch. In a review worktree an untracked file that git does
not ignore is not unique work (below).

For an agent's worktree the same five cases are read in the agent repository, and case 5 compares against
the shared repository's refs: a commit on the agent's branch that the shared repository does not yet hold
is unique. For an agent repository itself the rule refuses while any branch in it points at a commit the
shared repository does not hold under the same name. So an agent repository is removed only after the
runner's integrate has brought every branch across, and after its worktree has gone. Its stash entries
and its other refs go with it, so a stash entry in it, or a tag at a commit the shared repository does
not hold, is unique work too. An agent repository that the declarations give no shared repository to
compare with has unknown unique work, which is unique work: compared with itself, every branch would
hold itself.

Notes on the probes:

- Process use reads each process's working directory, open file links and mapped files from the
  kernel's process table. A command line that mentions the path is not use: that test also matches the
  shell doing the check. The file-sharing helper of a desktop container engine holds descriptors on every
  path a container ever mounted and is not counted; the containers' own mount lists are read instead.
  The helper is pinned by its identity and not by its name, which any process may take (amended
  2026-11-13, re-review): its command name, the uid of the installation's owner, the exact unit of that
  user's manager its cgroup file names, and the program its exe link leads to when that can be read.
  Every other process of that name is read and counted. A kernel thread is left out by the PF_KTHREAD
  flag in its stat file: it holds no working directory, descriptor or map of a user's path, and that is
  a fact of the kernel, not a judgement.
- The folder remover's rename closes the gap between probe and delete. A process that opens the folder
  after the first probe either fails to find it, or holds a file that the second probe sees under the new
  name.
- Unique work for a squash landing: the branch tip is not an ancestor of the trunk, but it is the source
  commit the completion receipt names, or an ancestor of it. That is why rule 5 reads the receipts.

What a probe cannot read (amended 2026-11-13). Every probe fails closed: what it cannot read or cannot
decide is in use, or is unique work, never free. The review of VELDO-0299 found five places where the
probes said "free" because they could not look, and each now says the opposite:

| What could not be read | What the probe says |
| :- | :- |
| A worktree git cannot read (for example a repository owned by another user, which git refuses) | Its locks are unknown: locked, and the path is in use. Its unique work is unknown: unique work |
| A scratch folder the probe cannot open, or a borrow journal it cannot look into | Locked, or not settled: in use |
| An agent repository with no shared repository to compare with | Unique work unknown: unique work |
| A process whose name, working directory, descriptors or maps cannot be read | Listed by process id and uid, and judged by the rule below |
| An engine the client cannot read | Named, and the path is in use |
| A process table mounted so that it hides other users' processes (hidepid) | The path is in use |

Unread processes: bounded fail closed (the lead's decision, 2026-11-13). The probe runs as the user who
owns the installation and has no root. On the measured host the kernel will not show it the working
directory, the descriptors or the maps of 536 processes: every root-owned process and kernel thread,
every other user's, and a few of its own. If each of them counted as use, every item on the host would
be deferred as in_use for ever, and that is what VELDO-0330 first reported (617 at that count). If none
counted, the probe would be blind to another user's process sitting in the folder. So an unread process
counts as use of an item only when it could reach that item, and the probe proves "could not" from facts
it can read without root:

- Who the process is. Its uid, its groups and its parent are in its status file, which every user may
  read. A process whose status cannot be read counts.
- The same uid counts. A process of the probing user is readable; one that is not (it made itself not
  dumpable) can be anywhere that user can be, so it counts for every item.
- Another uid is judged by the path's own permissions: the owner, the group and the mode of every
  directory from / down to the item, read with os.stat. A process counts when each directory gives its
  uid or one of its groups search permission and the item itself gives it any permission. When one
  directory shuts it out, it cannot have opened anything at or beneath the item, and it is excluded. A
  directory that owner, group and mode do not describe (it cannot be read, or it carries an access
  list) cannot be judged, and the process counts.
- A privileged process is not judged by the mode when a login started it (amended 2026-11-13, after
  the re-review, which found the first wording, "root judged by the mode", wrong as a fact). Root, and
  any process that holds CAP_DAC_OVERRIDE or CAP_DAC_READ_SEARCH in its effective capabilities, passes
  every mode check, so the mode says nothing of where such a process is. The status file gives the
  capabilities to every user. What tells a system daemon from a person's command is the loginuid, in
  /proc/<pid>/loginuid, which every user may read: the kernel sets it at login, it is kept across
  fork, exec and sudo, and it cannot be changed once set. A daemon started by the system has it unset.
  So a privileged process whose loginuid is set counts for every item: a command the user ran through
  sudo is the user's, also after the shell that started it has ended and it hangs under the first
  process; so is a cron job of root's. A loginuid or capabilities that cannot be read count the same
  way.
- A privileged process no login started, a system daemon, is judged by the mode like any other uid.
  That is a stated policy, not a reading of the kernel: the kernel would let it in, and the policy is
  that a daemon nobody logged in to start does not go into a user's folder it was not given. Such a
  process has two ways of its own to the item: the directories let its uid or its groups through as
  they would any user (a path under a world-readable folder, a root-owned folder), or a container
  engine mounts the path. So it is excluded only when the mode shuts its uid out and no container has
  a bind mount at, beneath or above the path. The engine probe's mount list is where that is read: it
  covers what dockerd and containerd bind. Otherwise it counts.
- A container mount is a way in for every unread process, not only root's. A process inside a
  container reaches a bound folder through the mount, whatever the host's directories say of its uid.
  So when any container, running or stopped, has a bind mount at, beneath or above the path, or an
  engine cannot be read, every unread process counts. (A mount at or beneath the path is use in its own
  right, by rule 4's first words. A mount above it is not use; it only ends the bound.)
- A container's process is judged by its container's mounts and by nothing of the host. Its cgroup
  file, which every user may read, names the container (an id of 64 hexadecimal digits). Its uid is a
  number of the container's own: a process there with the owner's uid number is not the owner's, and
  root there is not a login's. When an engine the probe read holds that container, the process has no
  reach of its own and counts only through the rule above, when a mount is a way to the path. When no
  engine that was read holds it (no engine is named, or the container is another engine's), its mounts
  are not known and it counts. A process whose cgroup file cannot be read cannot be told from one in a
  container, and counts.
- A child counts when a parent could reach. A process keeps the working directory and the descriptors
  it was started with, so a command the user runs through sudo or su is another uid, or root, sitting
  in the user's folder. The probe follows the parents in the status files, and a process any of whose
  parents counts, or cannot be judged, counts.

What this bound does not see. First, a process of another uid, without privilege, that kept a working
directory or a descriptor from a parent that could reach the item, after every such parent has ended.
Its parent is then a process that is shut out, and nothing the probe may read ties it to the item.
Second, a system service no login started (its loginuid is unset) that was configured to work in the
path: a unit with a working directory there, or a daemon told to write there. The policy above
excludes it where the mode shuts its uid out. The folder remover's rename (below) is what limits the
harm in both: such a process keeps its files under the new name until the delete, and the delete of a
file a process holds open does not take the data from that process.

What the probe needs, and how it gets it without root: read access to the status, stat, cgroup and
loginuid files of every process (the kernel gives that to every user; a kernel built without audit has
no loginuid file, and there every privileged process counts), os.stat on the item's directories (the
owner of the item has it), and a process table that shows every process. Under hidepid the table shows
only the user's own, the probe cannot list what it must judge, and rule 4 refuses every removal until
the table is mounted to show them. (This sentence first offered giving the service CAP_SYS_PTRACE
instead. The owner decided against that on 2026-11-13: the service never holds the capability, 7.1.) The
deferral names each process that counted, by process id, uid and the reason, so the owner can see why.

Measured on this host, 2026-11-13, for an item under the owner's home folder (mode 750): of 536 unread
processes 527 are excluded and 9 count. Six run under the user's uid number and are not readable. Five
of them are the user's own and not dumpable: the systemd user manager and its PAM helper, two processes
of the desktop container engine's backend and ssh-agent. The sixth is not the user's (corrected after
the re-review, which this paragraph first counted as "one short-lived command" of the user's): it is a
container's health check, in a container's cgroup, whose uid inside the container happens to be the
same number. Three are let through by the home folder's group: a root-owned session worker and a
root-owned mount helper that carry the user's group, and a container's process whose group id is the
same number. So on this host rule 4 still defers every item under the home folder, naming nine
processes where it named 617.

Measured again the same day with the re-review's rules, both engines named: 355 unread processes are
listed (the kernel threads are left out), 347 are excluded and 8 count. Five are the user's own, the
ones above. Three are root-owned and a login started them (the session worker and two mount helpers,
whose loginuid is the user's): they count as the user's, by the loginuid and no longer by the group.
The 169 processes in containers, the health check and the group's namesake among them, are judged by
their containers' mounts, none of which is a way to the item, and do not count. With no engine named
those 169 count, because their mounts are not known. The user's own undumpable processes are the open
point. A systemd user
manager is there on every host with a user session, nothing short of CAP_SYS_PTRACE reads it, and the
decision above says it counts. Whether the service is given that capability, or such processes are
bounded another way, is the lead's to decide; nothing is removed on this host until it is.

### 7.1 The process reader (VELDO-0344)

The owner's decision of 2026-11-13 (Telegram 41204 and 41205) closes the open point above. The probe
reads every process through a small separate program, the process reader. The reader holds one file
capability, cap_sys_ptrace, which the owner installs once with one sudo command. It reads entries of
the kernel's process table and prints facts. It never attaches to a process, never signals one and
never writes. There is no list of trusted process names. The Veldo service never holds the capability:
the reader is a program of its own, which the probe runs and which exits when it has printed. Without
the reader, or with one that is not the binary the owner installed, unread processes are judged by the
bound above as before, and the probe says so.

What one capability reads. Measured on this host on 2026-11-13 (kernel 7.0), against a process the
probe cannot read today:

| Entry of /proc/<pid> | Without the capability | With cap_sys_ptrace alone | What it gives |
| :- | :- | :- | :- |
| cwd, by stat through the link | Refused | Read | The device and inode number of the working directory |
| maps | Refused | Read | The device and inode number of every mapped file |
| fdinfo/<n> | Refused | Read | The mount id and the inode number of every open descriptor |
| mountinfo | Read | Read | The device of every mount id |
| fd, the folder of links | Refused | Refused | The paths of the open files |

The last row changes one word of the decision. The decision lists fd among what the reader reads. The
fd folder is mode 0500 and belongs to the process's uid, or to root when the process is not dumpable.
Listing it is an ordinary permission check, and cap_sys_ptrace does not pass it; it took
cap_dac_read_search as well before the folder could be listed. So the reader reads fdinfo in its place
and stays at one capability. The measurement ran in a container that shares the host's process table,
as uid 0 holding cap_sys_ptrace and nothing else, against a process of the owner's. The installed
reader runs as the owner against entries that belong to root, which is the same check from the other
side. A row that runs where the reader is installed proves it on the host (VELDO-0344).

Numbers, not paths. The reader prints device and inode numbers for all three facts and never a path.
There are three reasons. One capability gives no path for an open descriptor. A path is also the wrong
thing to compare: a process in a container or in a sandbox has its own mounts, and the path the kernel
prints for its working directory is not a host path, while the device and inode number are the same in
every mount namespace. And numbers disclose less to whoever runs the reader (below).

The reader:

- One C file, engine/scripts/veldo_procread.c with its synced copy, built static with the build line
  of veldo-userns, the repository's one other compiled helper (VELDO-0210). It has to be a compiled
  binary of its own: a file capability on an interpreter would be held by every script that
  interpreter runs. C because that is what the house already builds, reviews and gates for a helper of
  this kind; no second toolchain is added.
- Installed at /usr/local/lib/veldo/veldo-procread, owner root, group the installation owner's own
  group, mode 0750, capability cap_sys_ptrace=ep. So the owner's account can run it and no other
  account on the host can.
- It takes no argument, reads no input and no environment variable. With any argument it prints
  nothing and exits 2.
- Before it reads anything it sets no_new_privs and installs a seccomp filter that allows only what
  reading needs: open for reading, read, list a folder, stat, close, memory for its own buffers, write
  to its own standard output and exit. A call off that list ends the process. So "never attaches,
  signals or writes" is enforced by the kernel and not only by the source.
- For every process in the table that is not a kernel thread it reads stat (the start time and the
  flags), cwd by stat, every fdinfo entry, mountinfo and maps. It opens nothing outside /proc.
- The decision also lists cgroup and loginuid. Every user may read those two, and the probe keeps
  reading them itself, so the reader does not.

The output, exactly. ASCII lines ending in a line feed, fields separated by one space, every number
decimal:

| Line | Meaning |
| :- | :- |
| veldo-procread 1 cap=C | The first line. 1 is the format's version. C is 1 when the reader holds cap_sys_ptrace in its effective set, else 0 |
| p PID START | Opens the block of one process. START is field 22 of its stat file, its start time in clock ticks |
| c MAJOR:MINOR INODE | Its working directory |
| f FD MOUNT MAJOR:MINOR INODE | One open descriptor: its number, its mount id, the device mountinfo gives for that mount id, its inode number. The device is a single hyphen when the process's mountinfo has no row for the mount id |
| m MAJOR:MINOR INODE | One mapped file. Lines of maps with inode 0 are left out; a pair may repeat |
| x FACT ERRNO | A fact that could not be read. FACT is one of stat, cwd, fd, mnt, maps; ERRNO is the kernel's error number |
| g | The process ended while it was read. Closes its block |
| end COUNT | The last line. COUNT is the number of p lines |

Nothing else is written to standard output, nothing to standard error, and the exit status is 0. A
block for the user manager might read:

```
p 2114 5127
c 259:2 2
f 0 30 0:5 5
f 4 19 - 1058
m 259:2 19937837
```

How the probe checks that it is the expected binary, before every run:

1. The path is fixed in the probe. It is never taken from the environment, the installation or the
   project.
2. The file is a regular file and no link, its owner is root, its group is the installation owner's
   group, its mode is exactly 0750, and every folder from / down to it belongs to root and is writable
   by root alone.
3. Its capability attribute holds exactly cap_sys_ptrace, permitted and effective, and nothing
   inheritable.
4. Its SHA-256 digest equals the one in the installation's space section, key process_reader (6.8).
5. Its first output line says version 1 and cap=1. A reader started under no_new_privs or from a
   mount that drops capabilities gets none, says cap=0 and is not used.
6. Its output is whole: every line is in the format, the end line is there with the right count, and
   the exit status is 0.

A reader that fails a check is not run, or its output is not used, not even in part. The probe's
answer then carries the reader's state (absent, or refused with the check that failed) and every
unread process is judged by the bound. The digest is not what stops the owner's own account from
changing the binary; root ownership of the file and its folders does that. The digest ties the
installed binary to the build the owner made from the reviewed source, so a binary built from another
source, or replaced by another root act, is refused. An agent that edits the digest in the
installation's file can only make the check fail.

How the probe uses the facts. For an item it lists the item's folder and everything beneath it,
following no link, and keeps the device and inode number of each entry. On this worktree that is 9,011
entries in 0.3 seconds. A folder it cannot list makes the item in use. Then, for each process it could
not read itself:

- The reader's block is taken only when its process id and start time are the ones the probe reads
  for that process. A block with an x line, a missing block or another start time leaves the process
  unread, and the bound judges it.
- A process whose block is whole is read. It uses the item when its working directory, a descriptor
  or a mapped file has a device and inode number in the item's set, and it is named with the fact that
  matched. Otherwise it does not count, whatever its uid, its login or its parents: where it is has
  been read.
- A descriptor whose device is a hyphen (a pipe, a socket, or a file on a mount that was detached) is
  matched by inode number alone. A pipe whose number happens to equal a file's in the item defers the
  item once more than needed; nothing is ever freed by it.
- On a filesystem where a file's device number is not the one its mount row gives (the probe compares
  the two for the item itself), descriptors and maps are matched by inode number alone, the same way.
- A process the probe can read itself is judged from its paths as before. A process table mounted with
  hidepid still makes the path in use; this ticket does not change that.

A deleted file that a process still holds open is not in the item's set and is not use: removing the
item takes nothing from that process.

Install, by the owner, once, from the authority checkout's root. The first line builds the reader and
prints its digest; the second is the one sudo command:

```
d=$(mktemp -d) && g=$(id -gn) && cc -std=c11 -O2 -Wall -Wextra -Werror -static -ffile-prefix-map="$PWD"=. -o "$d/veldo-procread" scripts/veldo_procread.c && h=$(sha256sum "$d/veldo-procread" | cut -d' ' -f1) && echo "$h"
sudo sh -c "install -D -m 0750 '$d/veldo-procread' /usr/local/lib/veldo/veldo-procread && chown root:'$g' /usr/local/lib/veldo/veldo-procread && chmod 0750 /usr/local/lib/veldo/veldo-procread && echo '$h  /usr/local/lib/veldo/veldo-procread' | sha256sum -c - && setcap cap_sys_ptrace=ep /usr/local/lib/veldo/veldo-procread"
```

The capability is set last, because a change of owner clears it, and only after root has checked that
the installed copy has the digest the owner saw. If a process of the owner's account swapped the built
file between the two lines, the check fails and the copy is left with no capability. The owner then
writes the digest into the installation's space section as process_reader, and runs the probe's reader
check (python3 -I .veldo/control_space_probe.py reader), which prints the state and reads one
undumpable process it starts itself. docs/veldo-procread-setup.txt carries the same lines.

Uninstall, also the owner's. Either line is enough, and after either the probe reports the reader as
refused or absent and judges by the bound:

```
sudo setcap -r /usr/local/lib/veldo/veldo-procread
sudo rm /usr/local/lib/veldo/veldo-procread
```

Then process_reader is set to none.

What an agent running as the owner can do with it. It can run the reader, since it has the owner's
group. It learns, for every process on the host: the process id and start time, and the device and
inode numbers of its working directory, its open files and its mapped files, with descriptor numbers
and mount ids. It learns no path, no file name, no content, no memory, no command line, no environment
and no address from maps, so nothing about the memory layout of a root process. A number becomes a
name only for a file the agent can already reach and stat. So what it can newly answer is "does some
process, root's included, have this file of mine, or this file I can already see, open or mapped". That
is what lsof tells root, without the names, and it is accepted.

It cannot make the reader do anything else. The reader takes no input, so there is nothing to steer. It
is static, so no library can be loaded into it. The kernel does not let a process attach to one that
holds a capability it lacks, so the agent cannot take the capability over through the reader. It can
kill the reader or starve it of descriptors; the output is then cut or short, check 6 refuses it, and
the item stays. An agent inside Veldo's sandbox gets even less: the sandbox sets no_new_privs, under
which the kernel grants no file capability, and gives the agent a process table of its own.

What stays unread with the reader in use: a process that ends or changes while it is read, a kernel
too old to show inode numbers in fdinfo (before 5.14; every block then has an x fd line), and a hidden
process table. Each is judged as before.

A child holds its parent (amended 2026-11-13). Rule 6 was written as "present, due or deferred". The
review of VELDO-0298 reproduced the data loss that wording allows: an agent repository due at ticket
ended, whose worktree the owner had answered Keep for, came back for removal, and removing it takes the
kept worktree and the uncommitted files the owner chose to keep. The unique work rule does not catch
it: the branch was already across, and only the uncommitted files were unique. The same holds for kept
evidence inside a worktree (git's worktree remove takes it), for a declared child (being made right
now) and for a removing one (half removed). So a child holds its parent in every state but removed and
gone. Only a child that is due and is itself removed at the same event goes before its parent instead
of holding it. This is what 4.1 already says of kept: a present item that is kept.

Neither the kind registry's function nor rule 6 trusts a list of children it is handed. Each looks
for itself, at the moment of the attempt: at every item the ledger records inside this one, by its
parent and by its path, in whatever state; and, for an agent repository, at the worktrees its own git
folder registers that are on disk. A registered worktree on disk that no live item records holds the
repository, and so does a repository git cannot list. The function refuses a call whose list does not
hold every child the look finds, in the state it finds it.

A nested repository holds its worktree (amended 2026-11-13, re-review). The look read the disk only
for an agent repository's registered worktrees; for a worktree it read the ledger alone. The re-review
reproduced the loss that leaves: a git repository with a commit of its own, in a folder of a worktree
that git ignores, is no case of unique work (an ignored file is none), no item records it, and git's
non-forced worktree remove, the tool of rule 7, deletes it with its commit. So the look also walks the
folder of a worktree and of an agent repository, ignored or not, following no link, and names every
git repository beneath it: a folder that holds a .git entry, as a folder or as a file, or that is
itself a git folder. One that no live item records holds the item as unrecorded, and a folder that
cannot be listed makes the item's inside unread, which holds it too. A recorded item's folder is not
walked into: that item holds its parent by its state. A worktree with a submodule is held this way
until the submodule is recorded or gone, which is also what git's own remove says of it.

Retry. A deferred item is made due again by its next ending event, by admission requested on its pool
(sent once per hold, 6.7), and by reconcile. One more: when a pending retirement's obligation completes
and the retirement is carried out
(control_retirement.py:53-56, 334), that same call retries the dispatch's deferred items. The retry is
bound to the obligation completing. A sweep that finds the obligation unchanged does nothing to the items,
so the number of sweep calls, some of which follow a timer-woken pass, does not matter.

Unique work at the end of a ticket. A worktree deferred for unique work at ticket ended or project ended
has no further event of its own. So Signal raises one decision request in the owner's inbox. The same
holds for a worktree deferred for unique work at worktree abandoned, at released by its creator, and,
for a worktree owned by a run that is not a review, at run finished. Review worktrees do not get a
request each (below).

Which touchpoint. In the request vocabulary this is a decision choice (request.py:74-77), and its Discard
answer carries the irreversible impact, which that vocabulary raises to the critical tier (request.py:92,
236). That vocabulary is for request records kept in a repository. In the control store, requests are
settled by the settlement service, whose journey has five touchpoints today: grooming, admission,
priority, finding disposition and decision disposition (control_request_settlement.py:106-127). The
decision disposition touchpoint of control_backlog.py:185 approves an alternative outcome for a unit,
which is a different question. So the journey gains one touchpoint, space disposition, presented as a
decision and answered by the project owner. The lead has accepted this touchpoint.

The settlement and the channel have no tier: neither file holds the word. So the request cannot be
"presented as critical" on the control path. What that path does carry is the request's terms. They
state that Discard cannot be undone, and they list, for each worktree, the files Discard would lose
and, for a detached worktree with commits no ref holds, the kept branch those commits go to; the
presentation shows both, and the Ledger raises no request that offers discard without that list
(VELDO-0327).

How three answers fit a closed set of rulings. The set of rulings is closed in three places:
authority_contract.py:379 allows approve, reject and return for elaboration, and :414 refuses any other
ruling on a decision answer; the channel maps each offered choice to one of them and does not present a
decision whose choices do not all map (control_channel_presentation.py:173-175); and the settlement checks
the choice against its ruling (control_request_settlement.py:509, 571) and takes the effect from the
ruling (:670). Save, keep and discard as rulings would need all three places widened.

The design does not widen them. The channel already has a pick: the word accept followed by named values,
whose ruling is approve (control_channel_presentation.py:176-180, 254-265). A request for one
worktree offers exactly three choices, accept save, accept keep and accept discard. Each is a pick, each maps to approve, and an
answer that names none of the three is refused as unmatched_choice by the existing check. The journey
entry for space disposition names one effect, for approve. The effect record already carries the choice
beside the ruling (:670), and the Ledger reads the choice from it to know which of the three to apply.
Reject and return for elaboration are not offered; Keep is the answer that changes nothing. A review
group's request offers more picks of the same form (below).

So the change is one new entry in the journey configuration of control_request_settlement.py and the
Ledger's reading of the effect. authority_contract.py and the choice map are not touched, and the five
existing touchpoints are unchanged. It has its own ticket (VELDO-0327). Everything else is the existing
path: signed terms, one presentation, one settlement, one winner.

The request shows the worktree, its branch and the list of changed and untracked files, and has three
answers:

| Answer | What happens |
| :- | :- |
| Save | The changes are committed on a kept branch named for the ticket, authored as the owner's configured git identity. A worktree with no ticket gets a kept branch named for the run that owned it: the prefix space-saved, then the run's label. Then the worktree is removed by git's non-forced remove. When the tree is clean and only unlanded commits made the work unique, nothing is committed: the branch already holds them, it is kept, and the worktree is removed |
| Keep | The item's state becomes kept. Nothing retries it and no second request is raised. Abandon on the console ends that |
| Discard | The discard remover runs: git's worktree remove with the force option on that one worktree. Rules 1, 2, 3, 4 and 6 still apply, and the remover refuses if the list of files differs from the list the owner was shown. No commit is lost. The branch is kept, so every commit on it survives. A detached worktree whose commits no ref holds gets a kept branch at its checked-out commit before the remove, and when that branch cannot be created the discard does not run (6.5). What is lost is the uncommitted and untracked files the owner was shown |

Veldo never commits on its own. The commit in Save exists only because the owner's signed answer asked for
it. Discard is the one forced removal in Veldo, and it is allowed only after the owner's discard answer.
Outside review worktrees there is one request per worktree: later events for the same deferred item find
the open request and add nothing. For a worktree in a plain repository the request goes to the
installation's owner.

Review worktrees. The lead's decision (e) has two halves.

Review scratch. A review worktree is a read-only checkout, so an untracked file in it that git does not
ignore is review scratch and not unique work. At the review's run finished Signal runs the review scratch
remover (6.5) on the worktree first, path by path under rules 1, 2, 3, 4 and 6, and then removes the
worktree by git's non-forced remove, which now finds nothing to refuse. No request is raised. No force
option and no clean command is used, so Discard stays the one forced removal. A path a rule refuses, such
as a file a process still holds open, defers the worktree as in_use, and it is retried at its next event
like any other deferral.

Nothing a review produces is lost by this on the measured host. The review script writes its report and
its event log to a folder outside the worktree (codex_review.sh:46, :135-136), and it copies the
reviewer's capsules out of the worktree before it exits (:152-154), which is before the wrapper sends run
finished.

Everything else. A review worktree with a modified tracked file, a staged change, an operation in
progress or a commit made on its detached HEAD that no ref holds (cases 1, 2, 4 and 5) is deferred as
unique work. It never gets a request of its own. It joins the grouped decision request of its scope for
that day:

1. The day is the calendar day of the deferral event, in the installation's time zone. It is a key and
   not a schedule: nothing opens, closes or sends a request because the clock moved.
2. A deferral joins the open group of its scope and day when there is one: it adds its worktree and
   publishes a new version of that group's request. An answer bound to an older presentation settles
   nothing: the settlement already refuses it as stale_presentation
   (control_request_settlement.py:507-508). When there is no open group, because the deferral is the
   first of the day or because the owner has answered the day's earlier group, it writes a new review
   group record (4.9) with the day's next sequence number and raises a new request on the space
   disposition touchpoint. A scope has at most one open group per day. So the owner gets one request
   per day in the normal case, and a second one that day only when a worktree is deferred after the
   first was answered. The deferral event opens it; the clock still opens nothing.
3. A deferral on a later day opens that day's own request, whether or not an earlier day's request is
   still open. An earlier request is never added to and never closed by a later day. It waits for the
   owner's answer as it stands.
4. One answer covers the whole group, and the request also offers an answer for one worktree (the
   lead's decision (f)). The request lists the three group picks, accept save, accept keep and accept
   discard, and for each member three member picks that add the letter w and the member's short index:
   accept save w2, accept keep w2, accept discard w2. The request's text names each worktree beside its
   index. No item identity is ever a pick value; it holds a colon, and a pick value is a word of
   letters, digits, '_', '.' and '-' (control_channel_presentation.py:176-181), which w2 is. The channel
   does not change: a pick is accept and one or more values (:255-259), every pick has the ruling
   approve (:262-265), and the presenter checks a request's choices only for a ruling each and for
   being distinct (:866-879).
   - A group pick applies to every member still in the group, and the group closes.
   - A member pick applies to that member only. The member leaves the group, its answer is applied,
     and the request is settled like any other. When members are left, the Ledger raises a new request
     for them on the same group record and writes it in the record's request field; their indexes do
     not change. It is a new request and not a new version of the settled one, because the settlement
     refuses any answer to a closed request (request_closed, control_request_settlement.py:495). When
     the last member leaves, the group closes.
   - The choices and the answer instruction must fit one message part, or the presenter refuses to
     render (:377-379). When the group picks and three picks for every member do not fit, the request
     offers the group picks and the member picks of as many members as fit, lowest index first, and its
     text names the members that have no pick of their own in this request. Each member pick makes the
     next request shorter, so it reaches the members after them.
5. Save commits each worktree's changes on a kept branch named for the review run that owned it: the
   prefix space-saved, then the run's label. A worktree whose only unique work is a commit on its
   detached HEAD gets that branch at its HEAD and no new commit.
6. Discard compares each worktree's list of files with the list the group record holds for it. A
   worktree whose list has changed is not discarded; the others go. A detached member whose commits no
   ref holds gets its kept branch first, as in 6.5. A refused worktree is deferred again and placed as
   item 2 places any deferral of that day. After a group pick its group is closed, so it opens a new
   group with its own request.

How often this can happen on the measured host. The review script has a tests mode whose brief tells the
reviewer to write failing tests into the worktree (codex_review.sh:116-124). A new test file is review
scratch and goes with no request, which is what the script's forced remove does to it today. A test
added to an existing test file is a tracked modification, so a tests-mode review can put a worktree into
the day's request on any day it runs. However many do, the owner has one open request for that day at a time.

In report mode none of this happens until the owner confirms the group of due review worktrees, and the
host's review script keeps its own forced remove until core is in act mode (section 11).

The protect list. An entry is a path prefix, a Docker name pattern or a compose project name. A path is
protected when it is at, above or beneath an entry. A Docker object is protected, on every engine the
installation names, when one of these holds:

- its name matches a name pattern for its type (volume, container, image, network);
- its compose project label, com.docker.compose.project, equals a protected compose project name;
- it is a container that mounts a protected volume or a protected path;
- it is the image a protected container was made from, or a network one is attached to.

Name and label are tested apart. An object made by hand without the label is protected by its name, and
one whose name a compose override changed is protected by its label. A container is not protected only
because it runs an image whose name is on the list: a gate's own database container made from a common
image must still end with its run.

The list is read at declare, at adopt, at every proposal and at every removal. So a protected thing gets
no item record and no proposed owner. It is in no pending group, has no Adopt action under Reports and
is named in no decision request. It appears under space.protected, and that is all: the owner forbade
even offering to remove these things. Nothing on the list is ever removed by Veldo, in report mode or in
act mode, whatever its size and whatever event, Confirm, Discard or released record names it.

## 8. Data flows

### 8.1 A build run through the factory, start to end

1. Runner.prepare sweeps, then writes the hold and asks admit. Waiting (the project is in act mode):
   prepare refuses with space_wait, the unit is listed as waiting with the numbers, and nothing else is
   made. On later passes prepare asks admit again, and the answer changes only after a write that freed
   space on the pool (6.7). Advised (report mode) or admitted: go on.
2. Prepare reserves, and records the contract with its space field.
3. The provisioner declares the worktree (or clone work tree), its branch, its agent repository when the
   run is confined, and its scratch folder, makes them, and confirms each.
4. The receiver accepts, declares the run folders and the build root, sets the four environment values
   and starts the worker in its containment group.
5. The worker runs. Veldo does nothing during the run.
6. The worker and its group end. The receiver records the dispatch's end as it does today.
7. The receiver runs the census: new build output, Docker objects with the run's label, sizes.
8. The receiver calls Signal with run finished. Scratch, the run directory, containers, networks and
   volumes are removed. Build output is removed, or passes to the ticket's queued run on the same
   worktree.
9. The receiver releases the hold. The release marks the pool's waiting holds and raises the space wake,
   so the units waiting on that pool are judged again on the pass that follows.
10. The receiver exits.

### 8.2 A gate, with or without a host configuration

The gate script today writes the stamp and prints the verdict itself (engine/scripts/verify.sh:352-382;
scripts/verify.sh:449-480 in this repository's copy). The gate host only takes the lock, starts the gate
script again as a child and exits with its status, and it runs only where a gate_host.json exists
(engine/scripts/verify.sh:108). So the three space steps are in the gate script.

1. Where a gate_host.json exists, the gate host takes the host lock as today and starts the gate script
   inside it.
2. Before its first check, the gate script calls the helper's need step. The helper writes the hold and
   asks admit. Waiting in act mode: GATE: NOT STARTED with the numbers, exit 75, no stamp and no event,
   exactly the VELDO-0220 answer. Advised in report mode: one line with the numbers, and the gate runs.
3. The gate runs its checks. The gate script keeps a copy of its own output for the run in the gate's
   output folder.
4. Before the stamp, when a check failed, the gate script calls the helper's classify step with that
   copy. Section 8.9 says what it answers. On a no-space answer the gate script writes no stamp and no
   event, prints GATE: NOT JUDGED with the reason, and exits 75. NOT JUDGED is a new answer; nothing in
   the code has it today.
5. Otherwise the stamp is written. That is the verdict; nothing before this step removes anything.
6. After the stamp, the gate script calls the helper's verdict step: census of the gated worktree, then
   Signal with verdict recorded. The build folder goes; the evidence folder's caches go; the evidence
   stays. Then the hold is released.

With no central installation, or with space management off, the helper says so in one line and the gate
runs as it does today.

The gate script and the helper are protected paths. The ticket that changes them needs the owner's
recorded approval bound to the commit and proof.

Which gates this reaches. The change to engine/scripts/verify.sh reaches repositories initialized after
it. An existing project's scripts/verify.sh is its own catalog (section 3), so each bound project gets the
three calls by a change of its own, at its own first check and its own stamp point: for core that is its
485-line script, whose stamp is written near its end. The helper is the same file for all of them, read
from the authority checkout. Each such change is a spec in that project and touches a path protected
there, so each needs the owner's approval in that project. Three things make this more than an
instruction:

1. The CLI's space gate-check verb reads a project's gate script and says whether the three calls are
   there, each before or after the stamp as required.
2. Reconcile runs the same check for every bound project and lists the ones that fail under
   space.reports.
3. Until a project's gate has the steps, its gates are started through the run wrapper (6.9), which gives
   admission and removes the build output at run finished. What such a gate lacks is NOT JUDGED: a gate
   that dies on a full disk still stamps red. The wrapper records that end as an environment failure in
   the ledger and says so in the gate's output, which is what tells the reader the red is not evidence.

The order is the lead's decision. core's gate script gets the steps first, while core is in report mode,
and core goes to act mode only after that and after three clean report days. The wrapper-only cover is
for the time before a project's own gate change lands. No project is switched to act while its gate lacks
the steps: the mode command runs the gate check and refuses (6.1).

### 8.3 A landing by the landing station

1. The landing station records the completion receipt.
2. It calls Signal with landed for the unit. The unit's worktrees lose what build output they still have
   and are then removed by git; the agent repository follows when its branches are in the shared
   repository; the branch is marked contained and kept; image tags go.
3. It computes contained for the project's other recorded branches against the new trunk tip and calls
   Signal for each that became contained.

### 8.4 A landing by hand

1. Someone commits on a landing branch, or moves the trunk, with any git command.
2. git runs the reference-transaction hook. In the committed state the hook sees that a trunk or landing
   ref changed. It sends one packet to the authority, signed as space-observer: the repository, the ref,
   the old commit and the new commit. If the authority is not reachable it writes the same thing to the
   spool. Then it returns, and the git command ends. Nothing has been computed or removed.
3. The authority writes the event record. The journal has advanced, so the service calls the event
   consumer when it has answered the packet. The consumer starts the space worker with the record and
   returns; the service loop runs no git command for it.
4. The worker tests each recorded branch of that repository that has moved past its start commit
   against the recorded new commit. For each branch that commit contains, the worktree on it becomes
   due with the event contained.
5. For each due worktree the worker runs Signal: build output first, then the worktree by git's
   non-forced remove, then the agent repository; the branch is marked contained and kept. The record is
   marked consumed.

Between step 2 and step 5 there is no wait on a clock. With the service running, the removal starts as
soon as the service has answered the hook's packet. With the service down, it starts when the service
next starts and replays the spool.

### 8.5 A hand-made worktree, and a branch switch in it

1. Someone runs git's worktree add in a bound or plain repository.
2. git runs the post-checkout hook in the new worktree. The hook records the worktree and its branch,
   with the start commit, the owner the branch pattern gives, and the creator "hook".
3. From then on the worktree has the events of section 5. A gate run in it removes its build output at
   the verdict. A landing that contains its branch removes it.
4. Later someone switches that worktree to another branch. git runs the same hook, this time with a real
   previous HEAD. The hook sends rebranch: the item now names the new branch and that branch's commit as
   its start. A landing that contains the old branch no longer touches this worktree.

A review's throwaway worktree is the other case. The review script runs under the run wrapper and adds a
detached worktree with plain git. The hook finds the run's space label in its environment and a detached
checkout, and records the worktree with the run as owner; the run's station, review, makes it a review
worktree. When the review command and its group have
ended, the wrapper's run finished removes the worktree's build output, then its review scratch (any
untracked file git does not ignore), and then the worktree, by git's non-forced remove. No request is
raised for that. A review worktree with a tracked modification or a commit of its own is deferred and
joins the day's grouped request (section 7).

### 8.6 A deferral and its retry

1. Signal finds a build folder due. Rule 4 finds a process with an open file in it.
2. The outcome is deferred, in_use, with the event that refused it. The console lists it.
3. Later the ticket's next run finishes. Signal makes the folder due again, the rules pass, it is
   removed, and the removal names this second event.

### 8.7 A lead session

1. The client starts a session. Its SessionStart hook sends one session started event (the session id,
   working folder, process id and process start time) and declares the session's scratch folder. The
   owner is the session, with the project or plain repository its working folder is inside. When the
   working folder is inside none, the owner is the session with no project. The scratch is recorded
   either way.
2. The service hands the session started record to the space worker. The worker looks at every session
   recorded on the host, whatever its project and including those with no project. For each whose
   recorded process the kernel no longer shows, the scratch becomes due with session ended and is
   removed. The lead's decision names the next session start on the same project; looking at every
   session on the host includes that case and is the only rule that also reaches a crashed session with
   no project.
3. The session runs. Worktrees it adds are recorded by the git hook, not by the session.
4. The client ends the session. Its SessionEnd hook sends one session ended event and returns. The
   client gives a hook a short time limit (the pack's existing hook has 15 seconds) and the session is
   on its way out, so the hook removes nothing. The space worker consumes the record and removes the
   scratch through the rules.
5. A session that crashes runs no SessionEnd hook. Its scratch stays until step 2 of the next session
   started anywhere on the host, or a reconcile.

A hook that fails or cannot reach the authority spools and returns; it never blocks the session.

### 8.8 Reconcile

1. Replay the spool.
2. Snapshot. For each bound and plain repository, git's own list of worktrees and branches, and whether
   its hooks are in place. For each bound project, whether its gate script has the space steps. For each
   agent repository found under a worktree root, its own list of
   worktrees and branches, because the shared repository's list does not show an agent's worktree. For
   each worktree root, scratch root, build root and the state root, the entries one level down. For each
   worktree found, the census of section 6.3. For each engine, the adapter's snapshot.
3. Subscribe. The Docker adapter's event streams. On disk there is nothing to subscribe to: the creators
   report through the seam and the hooks, and the census reads the rest at events.
4. Compare, and for each difference do one thing:

| Found | Ledger | Result |
| :- | :- | :- |
| Thing | Matching item | Matched; size refreshed |
| Nothing | Item present, declared, due or deferred | gone |
| Half-removed folder under its marked name | Item removing | Removal completed |
| Worktree in a bound repository's list, under the project's worktree root, on a branch the branch pattern maps to a ticket | None | Adopted, owner that ticket |
| Worktree as above, branch maps to no ticket | None | Adopted, owner the project only. It ends on contained, project ended and Abandon |
| Worktree in a plain repository's list, under its worktree root | None | Adopted, owner the repository only |
| Agent repository under a worktree root, with the shared repository as its alternate | None | Adopted, with its worktrees as children, owner by the branch pattern |
| Folder matching the project's build output patterns inside an adopted or recorded worktree | None | Adopted, parent that worktree |
| Folder directly under a declared build root whose name is the name of a worktree item | None | Adopted as build output, parent that worktree |
| Clone folder with a valid manifest under the state root | None | Adopted, owner the manifest's dispatch |
| Run directory under the runs root named for a dispatch the store holds | None | Adopted as scratch, owner that dispatch |
| Session scratch folder matching the installation's pattern | None | Adopted as scratch, owner the session id in its name, with the project or plain repository the folder's name gives; when the name gives none, no project |
| Batch clone or observation folder under the workspace root, named by a batch record the store holds | None | Adopted as scratch, owner that batch |
| Sandbox launcher scratch inside a recorded run's scratch root | None | Adopted as scratch, child of that scratch root |
| Sandbox launcher scratch directly under a scratch root or the temporary folder, belonging to no recorded run | None | Reported, with its size. Never removed by Veldo, whatever its age |
| Recorded worktree whose checked-out branch differs from the item's branch | Item present | The item's branch and start commit are updated, as rebranch does |
| Bound project whose gate script lacks the space steps | | Reported by name under space.reports |
| Docker object with a Veldo run label or a run's compose project name | None | Adopted, owner that run |
| Docker object whose compose working folder, configuration file or bind source is inside a recorded worktree | None | The worktree's project in report mode: reported with that worktree as the proposed owner. In act mode: adopted, parent that worktree |
| Anything on the protect list | None | Listed as protected. No item, no proposed owner and no Adopt action |
| Anything else under a root or on an engine | None | Reported |

5. For each adopted item, read its owner's current state and mark the item due if an ending event for it
   is already in the past (its ticket landed last week; its session's process is gone). For a project in
   act mode these go through Signal at once. For a project in report mode they wait for the owner's
   confirmation, and each is a proposal the owner can mark wrong.

Entries in the temporary folder outside the scratch roots the installation names stay reported and are
never adopted or removed. Nothing proves who made them. The same holds for loose files directly under a
scratch root.

Build folders under a session scratch root or a build root are adopted only when the folder's name is the
name of a worktree item. Others are reported until the owner adopts them. The measured host has none
today.

Reconcile is the only place where an action follows from a state instead of from an event as it happens.
It runs at service start and when asked, and never on a schedule.

### 8.9 A run that hits a full pool

1. The run or gate ends without success.
2. The receiver, the wrapper or the gate helper reads the pool's free space, before the census and
   before any removal, and searches the run's output for the operating system's no-space error.
3. Both true (the error is there, and free space is under the floor): the end is recorded as
   environment_failure:no_space. No verdict is written, a gate answers NOT JUDGED with exit 75, and the
   unit is not charged a failed attempt.
4. The error is there and free space is not under the floor: the end is unknown_outcome:no_space_unconfirmed.
   No verdict is written and the run is repeated once. A second end of the same kind stands as what it is.
5. Either way the census and Signal run as for any finished run, with one exception: rule 5 keeps the
   worktree, because a run killed mid-work leaves uncommitted changes, and the next brief for the ticket
   says the worktree holds them.
6. The unit goes back behind admission. Two environment failures in a row for one unit raise an andon to
   the owner and stop the repeats.

The classification is on whenever space management is enabled, in report mode as well as act. It removes
nothing and blocks nothing; it only stops a full disk from being recorded as a red.

## 9. Deployment view

```
  ONE HOST
  +=========================================================================================+
  |                                                                                         |
  |  Authority service (one process)          Factory state root                            |
  |    control store  <- - - - - - - - - - -   control.sqlite3 (ledger records live here)   |
  |    spool replay, then Reconciler            clones/ caches/ artifacts/ receipts/ runs/  |
  |      at start                               space-spool/                                |
  |    mode per project (ledger records)                                                    |
  |    event consumer, called after a                                                       |
  |      packet advanced the journal          Installation folder                           |
  |    Docker adapter: one event pipe           installation.yaml (space section)           |
  |      per engine context, in the             keys of space-observer and space-runner     |
  |      loop's poll set                                                                    |
  |    wake source "space"                    Project A repository        Project B ...     |
  |       |                                     .veldo/space.yaml                           |
  |       v  starts, pipe in the poll set       scripts/verify.sh with the space steps      |
  |  Space worker (child, one at a time)        hooks: post-checkout, reference-transaction |
  |    space library: removes for hook          worktree root                               |
  |    events and the service's own events        worktree, build output                    |
  |                                               agent repositories                        |
  |  API process  -> console in the browser                                                 |
  |                                           Plain repository (no Veldo in it)             |
  |  Receiver (one per dispatch)                the same two hooks, its worktree root       |
  |    space library, in line                                                               |
  |                                           Scratch roots                                 |
  |  Gate script + gate space helper            run scratch, session scratch                |
  |    (one per gate), in line                                                              |
  |                                           Build roots                                   |
  |  Landing station                                                                        |
  |    space library, in line                 Client account folders                        |
  |                                             SessionStart and SessionEnd hooks           |
  |  CLI as the run wrapper                                                                 |
  |    space library, in line                                                               |
  |                                                                                         |
  |  CLI started by a git hook or a                                                         |
  |    session hook: sends one packet or                                                    |
  |    writes one spool file, then exits                                                    |
  |                                                                                         |
  |                                           Container engine 1: data root on the          |
  |                                             filesystem (same pool as the filesystem)    |
  |                                           Container engine 2: data in a disk image      |
  |                                             (a pool of its own)                         |
  +=========================================================================================+
```

Who may write what:

| Process | Writes the ledger | Removes things |
| :- | :- | :- |
| Authority service | Directly; it is the store's writer | Nothing itself. Its event consumer only hands each event record to the worker |
| Space worker (child of the service) | Through the authority, as the authority principal | It works out what a hook's event made due, then removes: contained from a ref hook, session ended, released, ticket ended, project ended, Abandon, a confirmed group, and reconcile's completions |
| Receiver, gate helper, landing station | Through the authority, as signed commands | Yes, in line, at their own events |
| CLI as the run wrapper | Through the authority as space-runner; to the spool when it is not reachable | Only what Signal does for its own run's run finished |
| CLI from a git hook, a session hook or a host script's record and event calls | One record or event, as space-observer; to the spool when the authority is not reachable | Never |
| Worker (the agent) | Never. It has no store connection | Whatever its own commands do inside its worktree, as today |
| API | Owner actions, through the authority | No. Abandon and Confirm make the authority act. Marking a proposal wrong and the mode switch remove nothing |

Several hosts. An item names its host. Signal acts only on items of the host it runs on; an item on
another host becomes due and is carried out by that host's receiver or service at its next event or
reconcile. This design builds and proves one host. The second host is covered by the same records and is
not exercised until a ticket asks for it.

Order of start: the authority service opens the store, attaches the Ledger, replays the spool, consumes
the event records that replay left, then runs reconcile (snapshot, subscribe, compare) before it accepts a
dispatch. A reconcile that fails is reported
by name and the service serves everything else; admission then uses the last known holds and the live free
space.

## 10. Console

One new screen, Space, in the factory group of the navigation.

| Section | Shows |
| :- | :- |
| Pools | One row per pool: capacity, free, floor, held; under it the waiting runs, and in report mode the runs that would have waited, with need, free, held and floor |
| Usage | A table that groups by project, then ticket, then kind, with bytes and counts; each size names the event it was measured at. Each plain repository is a row beside the projects, and "No project" is one row holding the scratch of sessions started outside every project |
| Modes | One row per project, per plain repository and for no project: report or act and since when. For a row in report mode: the last three calendar days, each marked clean or not with the reason (no event that day; a proposal marked wrong), the wrong-proposal records, and the Act button. Beside the button the row names what still blocks the switch: a day that is not clean, each unconfirmed pending group by kind with its count, a gate script without the space steps. The Ledger accepts the switch only when nothing is left. For a row in act mode: Back to report |
| Pending removal | Due and deferred items with the reason in words (in use by process 4412; uncommitted changes in 3 files), the event that will retry, and the open decision request when there is one. The review worktrees of one group are listed under their one request, each with its index and the three answers for it alone |
| Removed | The removal history: what, whose, which event, how much, free space before and after; for an engine pool the note that the host figure did not change |
| Reports | Things found with no owner, each with Adopt and with the proposed owner when a rule gives one; Docker objects no run could be named for; loose files under a scratch root with their total size; repositories whose hooks are missing; projects whose gate script lacks the space steps |
| Protected | The list in force, and what each entry matches on each engine. Nothing in this section has an action |

Elsewhere: the run view gains a space panel (the run's items, their sizes, what was removed at its end);
the runs list shows a waiting run's reason in one line; the overview shows a pool under its floor.

For a project in report mode the Pending removal section groups due items by project and kind with one
Confirm per group. Each due item, each adopted item and each proposed Docker owner also has Wrong, which
asks for a reason, takes the item out of its group and writes the wrong-proposal record.

## 11. Migration

The order is the lead's decision: core first. core's gate gets the space steps while core is in report
mode; core goes to act only after three consecutive clean report days; then each other project goes the
same way.

Order on an existing host:

1. Set up the installation folder and start the authority service. The measured host has neither today,
   and nothing in this design works without them. The service has to stay running from here on: it is
   what consumes the hooks' events.
2. Write the space section with the protect list below, and bind the repositories. Binding installs the
   git hooks. Name the plain repositories and the client account folders; the hooks go in. No scope has
   a mode record yet, so every project, every plain repository and no project are in report mode.
3. The service starts, reconciles, adopts and reports. Nothing is removed. Admission advises. Reports
   lists every bound project whose gate script lacks the space steps; on the measured host that is all
   of them.
4. The owner reads Reports and Protected, and adds what is missing to the protect list.
5. The host's launch scripts are changed to use the mechanisms (table below). The gate launcher starts
   the gate through the run wrapper. It keeps its own 60 GB refusal and its own build folder delete, the
   review script keeps its forced remove and the sandbox script keeps its two deletes, all for now:
   in report mode nothing else refuses a gate or removes these things.
6. core's gate script gets the three space steps, by core's own spec and the owner's approval there
   (VELDO-0325). core is still in report mode. From here a core gate that dies on a full disk answers
   NOT JUDGED and stamps nothing, because the classification is on in report mode too.
7. core runs in report mode. The owner reads core's pending groups and proposals, marks wrong any that
   are wrong, and confirms the groups that are right, one kind at a time. Each confirmation runs Signal
   for that group through all seven rules.
8. When core has three consecutive clean report days and no unconfirmed pending group, the owner
   switches core to act. The Ledger reads the three days and the pending groups from its records and
   runs the gate check on core's gate script, and it refuses the command if any of the three fails; a
   proposal marked wrong starts the count again from the next day. From here core's removals happen at
   events and admission blocks core's runs and gates.
9. Only now remove from the host scripts what core's act mode replaces: the gate launcher's 60 GB
   refusal and build folder delete (gate_core_cand.sh:32-37 and 41), the review script's forced remove
   (codex_review.sh:51), and the sandbox script's deletes for core's agent repositories
   (agent_sandbox.sh:246 and 476).
10. Each other project follows the same sequence, the largest first: its gate script gets the steps in
    report mode (step 6), it runs three clean report days (step 7), the owner switches it to act (step
    8). A plain repository has no gate; it needs the three clean days. So does no project. Until a
    project's own gate change lands, the wrapper covers its gates, and it stays in report mode.
11. Retire the nightly script, by the check below. Not before core and no project are in act mode,
    because the script's five classes are core's worktrees and the session scratch.

What makes a day clean, exactly. The day is a calendar day in the installation's time zone. The scope was
in report mode for the whole day. The ledger holds at least one event, Signal call or reconcile for that
scope dated that day, so three days on which nothing happened prove nothing and do not count. And no
wrong-proposal record for the scope is dated that day. The switch needs the three days before today to
be clean and no wrong mark dated today.

Two more conditions are not about days (6.1). The scope has no unconfirmed pending group when the owner
sends the command, so every due item was confirmed or marked wrong first. And a bound project's gate
script has the space steps. The rule still cannot tell whether the owner read the adoptions and the
proposed Docker owners; for those the signed switch is the owner's statement that they did.

Values for the measured host (provenance; the lead's decisions of 2026-11-13):

| Setting | Value |
| :- | :- |
| Filesystem pool floor | 20 GB |
| Default need, gate | 50 GB, so a gate starts with 70 GB free. Today's rule is 60 GB |
| Default need, builder | 16 GB, so a builder starts with 36 GB free. Today's rule is 40 GB |
| Default need, review | 16 GB |
| Switch to measured needs | After five finished runs per project and station |
| Report mode | Admission shows "would wait" and does not block. Per project |
| Act mode | Per project, by the owner's command, after three consecutive clean report days, with no unconfirmed pending group and with the space steps in the project's gate. core first |
| Time zone for the day count | The host's own |

The protect list for the measured host, written into the installation before the first reconcile. It is
the lead's list, complete. Every entry applies on both engine contexts, default and desktop-linux,
whether or not the object exists there today. Nothing on it is ever removed by Veldo, in any mode, by any
event, any rule or any owner action in this design, and nothing on it is ever proposed for removal.
Taking an entry off the list is an edit of the installation by the owner. The names in the table were
read on the host on 2026-11-13 with read-only listings of volumes, containers and images.

| Entry | Identified by name | Identified by label | Present today on |
| :- | :- | :- | :- |
| The places database volume | Volume places_pg_places | Compose project places | Both contexts |
| Every places container | Container names that start with places- (places-postgres-1, places-api-1, and the three places-enrichment-worker containers) | Compose project places | places-postgres-1 on both; the other four on desktop-linux |
| Every places image | Image names that start with places- (places-api and the three places-enrichment-worker images), and postgis/postgis, the image the places database runs | The image of any container whose compose project is places | The places- images on desktop-linux; postgis/postgis on both |
| Any other places volume, and every places network | Names that start with places_ | Compose project places | Covered by the pattern |
| The places repository with its data and backups folders | The path ~/projects/places | | The host filesystem |
| Docker.raw and its folder | The path ~/.docker/desktop/vms/0/data | | The host filesystem |
| The cms database volume | Volume cms_cms-postgres-data, and every volume whose name starts with cms_ | Compose project cms | Both contexts |
| The loyalty database volume | Volume loyalty_loyalty-postgres-data, and names that start with loyalty_ | Compose project loyalty | desktop-linux |
| The referral database volume | Volume referral_referral-postgres-data, and names that start with referral_ | Compose project referral | desktop-linux |
| The supportbot database volume | Volume supportbot_pgdata, and names that start with supportbot_ | Compose project supportbot | desktop-linux |
| The notifications database volume | Volume notifications_notifications-pgdata, and names that start with notifications_ | Compose project notifications | desktop-linux |
| The travelbot database volume | Volume travelbot_pgdata, and names that start with travelbot_ | Compose project travelbot | Both contexts |
| The viraestetika database volume | Volume viraestetika_pgdata, and names that start with viraestetika_ | Compose project viraestetika | Both contexts |
| The seo-engine database volume | Volume seo-engine_seo-engine-postgres-data, and names that start with seo-engine_ | Compose project seo-engine | default |
| The seoeng cms database volume | Volume seoeng_cms-postgres-data, by exact name | None; the compose project name seoeng is not protected | default |
| The MinIO data volume | Volume docker_minio_data, by exact name | None; the compose project name docker is not protected | Both contexts |
| Images that cannot be pulled again | Image names minio/minio and minio/mc, any tag | None; an image carries no compose label | Both contexts |
| Any other project's database volumes | The patterns the project adds in its space file | The compose project names it adds | |
| The integration checkout and the gate's own checkout | Their paths | | The host filesystem. Their caches are reused by every full check; the nightly script's keep list today |

Protecting a compose project name protects every volume of that project, its media and static volumes
too, and not the database alone. That is on purpose: the owner's rule is that data is never a cache, and
no Veldo run uses these project names, because a run's compose project name comes from its own label
(6.3).

The listing showed two more volumes that hold real data and were not on the lead's first list:
seoeng_cms-postgres-data (compose project seoeng, on default) and docker_minio_data (the MinIO data
volume, on both contexts). The lead confirmed both on 2026-11-13 (decision (h)), and they are rows of
the table, each by exact name. Their compose project names, seoeng and docker, are not protected. The
lead did not ask for that, and docker is the name compose gives a project started in any folder called
docker, which is too broad to protect by label.

The owner's own scripts rotate the places backups (his order of 2026-11-07). They are outside Veldo and
are not changed. Veldo itself never removes a file under the places folder.

Host wiring (provenance). Each row replaces a place where a script acts alone today:

| Script | Change |
| :- | :- |
| myday/scripts/claude_run.sh:41 and codex_run.sh:32 | The client is started through the run wrapper |
| myday/scripts/codex_work.sh:130-132, codex_review.sh:55 | No change needed for recording: these call plain git, so the hook records the worktree. The review run is started through the run wrapper with the station review, so its detached worktree is recorded as a review worktree owned by the run. codex_review.sh:51 keeps its forced remove until step 9 and loses it there |
| myday/scripts/agent_sandbox.sh:257-266 | The private repository and worktree are made by the engine's sandbox prepare, which declares them; the script's own fallback calls the CLI's record verb, signed as space-observer, because its guarded git runs with hooks off |
| myday/scripts/agent_sandbox.sh:246 and 476 | At step 9 the recursive deletes become the CLI's event verb with the type released, signed as space-observer. The remove command's own containment check and force flag go with them |
| myday/scripts/gate_core_cand.sh:37, the gate command | Started through the run wrapper, inside the lock (step 5) |
| myday/scripts/gate_core_cand.sh:32-37 and 41 | The free-space refusal and the build folder delete stay through steps 5 to 8 and are removed at step 9. The wrapper covers core's gate from step 5; core's own space steps arrive at step 6 |
| myday/scripts/host_heavy.sh:9 | The command is started through the run wrapper, inside the lock |
| The gate lock's log folder | Named as a scratch root; gate logs are evidence items of their gate |

The nightly script's cases and what covers each. The script has five find lines and a keep list:

| The script removes | Covered by |
| :- | :- |
| Folders named target in the project's worktrees, to four levels | Build output by census (any ignored folder) in recorded worktrees, by declared patterns in adopted ones; removed at run finished, verdict recorded, landed or contained |
| Folders named target- and a suffix, to two levels | The same; the name does not matter |
| Folders with target in the name under the session scratch root | The run's build root and scratch root, declared by the receiver or the run wrapper; older ones adopted as scratch |
| Per-session scratch folders | Session scratch, recorded at session start and removed at session ended |
| Folders with target in the name under the user's cache folder | Named as a build root in the installation; adopted by the build root rule, then owned like any other |
| Its keep list (two checkouts) | Protect entries |

While both run. Until it is retired, the nightly script keeps running beside report mode. It would delete
a folder a safety rule had just kept, so before each removal it asks the ledger through the CLI's covers
verb, and skips any path whose item is deferred, kept or protected.

The retirement check. The script's dry run lists only folders unchanged for 2 days and at least 100 MB
(nightly_build_cleanup.sh:17-18, 88-91), so by itself it would show old, large folders only. The check
therefore runs the script's five find lines as a read-only listing with the age and size tests off, on
the live host on three days. On each day every path listed must already be an item in the ledger. The
result is read per class: a class with a path the ledger does not hold is a gap, the check names it, and
the script stays. When all five classes pass on all three days, remove the script's schedule entry and
keep the file. The check can pass honestly only after steps 2, 5 and 8, because those are what make the
host's own creators event sources and put core in act mode.

Two of the script's classes are adopted only by name: a build folder under the session scratch root or
under the cache folder becomes an item when its name is the name of a worktree item, and is reported
otherwise. The host has no such folder today. If one appears, the check fails on it until the owner
adopts it, which is the right answer for a folder nobody can name an owner for.

## 12. Tickets

Each ticket is one concern and becomes its own spec. The numbers VELDO-0296 to VELDO-0343 are reserved by
this design, forty-eight tickets. On 2026-11-13 no spec file on any of the repository's 508 refs or in
any worktree, and no commit on any ref, held a number above VELDO-0295 except this design's own commits.
Revision 5 kept the numbers of revision 4 and added 0339 to 0341. Revision 6 keeps them and adds 0342
and 0343, which no spec file and no commit on any ref held, so nothing that already cites a number
changes meaning. "Row" is a row of a suite; each falsifier is the one change that must turn its row red.

VELDO-0344, the process reader, was added on 2026-11-13 by the owner's decision, the forty-ninth
ticket. On that day no spec file on any of the repository's 508 refs or in any worktree, and no commit
message, held that number.

Build order: 0296, 0338, 0297, 0326, 0331, then 0298, 0299, 0330 and 0300 together, 0301, 0344, then 0302,
0303 and 0305 to 0314 with 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341 in any order, then
0304, then 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319, 0320, 0332, 0325, 0339, 0321, 0322.

0344, the process reader, comes straight after 0301: before any ticket that removes on a real host,
and long before 0320 (Confirm in report mode) and 0332 (the switch to act). Until the owner has
installed it, the probe judges unread processes by the bound, and on the measured host that defers
every item under the home folder.

0304, the boundary check, comes after 0302, 0303, 0324 and 0333 on purpose. Until those four have landed,
the paths in the Replaced table of 6.10 still hold removal primitives and the two removals by age, none
of them on the reviewed list, and the check would turn the gate red on its first run.

Tickets that touch protected paths and need the owner's recorded approval: 0302 and 0324 (the sandbox),
0309 (the gate script template, and the new helper added to the protected list), 0304 (its check is
called from scripts/verify.sh, policy.yaml:83), 0333 (the gate's leg timing), 0344 (the process reader's
source, which it adds to the protected list). 0325 produces a change to
the gate script of each bound project, approved by the owner in that project.

### VELDO-0296 Declarations: the installation's space section

Components: Declarations reader. The project's space file is VELDO-0338.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An installation with no space section has space management off and is not refused | Refuse an installation without the section; the row that reads the fixture installation with none is refused and fails |
| AC2 | With the section present, a missing key is refused by name and a malformed one by name | Give a missing floor a built-in value; the row with the floor key left out is accepted and fails |
| AC3 | The fixture installation's protect list, read back, holds each of its entries: an engine image folder, a repository folder, name patterns for a volume, a container, an image and a network, two compose project names and two image names, each returned for both of the fixture's engine contexts | Remove one entry from what the reader returns; that entry's row fails |
| AC4 | The section has no mode key, and one written into it is refused as unknown, so an edit of the file cannot look like a mode switch | Accept a mode key and ignore it; the row with mode: act in the section is accepted and fails |

### VELDO-0297 The ledger: item, pool, hold and reconcile records in the control store

Depends on 0296 and 0338 for the known roots and the protect list, and on the pool's device identity.
Components:
Ledger.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The commands of 6.1 write items through the states of 4.1 and no other move is accepted: confirm only from declared, outcome only from due or removing | Accept outcome removed on a present item; the row that sends it without a signal sees the item removed and fails |
| AC2 | Only the Ledger's module writes these entity kinds; the store's generic entity command is refused for them | Leave the kinds undeclared; the row that writes an item through the generic command succeeds and fails |
| AC3 | declare refuses a second live item at the same locator, a locator outside every known root, and a locator on the protect list | Compare locators as raw text; a second declare through a path with a trailing separator is accepted and the row fails |
| AC4 | A store rebuilt from its journal holds the same items, pools and holds | Keep sizes in a side table outside the journal; the rebuilt store's item has no size and the row fails |

### VELDO-0298 The kind registry and the lifecycle table

Components: Kind registry. Pure data and one function; no file, process or store access. Whether the
ticket has a queued run on the same worktree is a fact the caller passes in.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | For every kind and every event the function returns exactly the action of the table in section 5; the rows are the whole table, cell by cell, with the two rows for a worktree owned by a run (a review run, and a run of another station), session ended and released by its creator | Give worktree the action remove at run finished; that cell's row fails |
| AC2 | A worktree is never returned for removal while a child item is present, due or deferred, an agent repository never before its worktree, and due items come back children first | Return items in ledger order; the row with a deferred build folder gets its worktree first and fails |
| AC3 | Build output at run finished passes to a queued run of the same ticket on the same worktree when the caller says one exists, and is removed when it says none does | Remove whenever the owning run is finished; the row with the queued-run fact set loses the folder and fails |
| AC4 | An item keeps the table version it was declared under, and a registry change does not alter what an existing item ends on | Read ends_on from the current registry; after a fixture registry change the old item's events differ and the row fails |

### VELDO-0299 The probes: in use and unique work

Components: Probes. The rule order, the ledger rule and the protect rule are VELDO-0330.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A path is in use when a live process has its working directory, an open file or a mapped file at or beneath it, or a running or stopped container has a bind mount there; a command line naming it is not use | Check the working directory only; the row with an open file beneath the path reads not in use and fails |
| AC2 | A worktree has unique work in each of the five cases of rule 5. A branch with a commit that only its own ref holds is unique work; the same branch after a squash landing whose receipt names its tip is not | Count the worktree's own branch among the refs that contain the commit; the row with an unlanded commit reads no unique work and fails |
| AC3 | For an agent's worktree and an agent repository the comparison is against the shared repository's refs: a branch the runner has not brought across is unique work, and after it is brought across it is not | Compare inside the agent repository only; the row with a branch not yet brought across reads no unique work and fails |
| AC4 | A sandbox launcher's scratch is in use while its scratch lock is held or its borrowed login is not settled, and not in use once both are clear | Read the lock only; the row with a free lock and an unsettled login reads not in use and fails |

### VELDO-0300 The removers

Components: Removers.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A folder is removed by rename, second probe, delete. The row injects an open file between the first probe and the rename through the probe's test seam, so the order is fixed; the folder comes back under its own name | Delete after the first probe; the row finds the folder gone and fails |
| AC2 | A worktree is removed only by git's non-forced remove, and a refusal by git is the deferral remove_refused with the worktree untouched | Pass the force option; the row with an untracked file loses it and fails |
| AC3 | No remover runs a prune command, and none but the discard remover passes a force option; the row reads every command each remover ran | Use the engine's volume prune for volumes; the command row fails |
| AC4 | Each remover returns the item's bytes just before and the pool's free space before and after, and for an engine image pool the host figure apart | Report the engine's own reclaimable figure as freed; the row that compares it with the measured free space fails |

The builder verifies with a test what git's non-forced worktree remove does with ignored files, and
records the result in the proof. The design does not depend on the answer, because build output is removed
before the worktree.

### VELDO-0301 Signal: an event removes what is due, in the calling process

Components: Signal. Depends on 0297, 0298, 0299, 0300.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A call with an event makes the matching items due, carries each out through rules and remover, and writes each outcome before it returns | Return after marking due and remove on a later call; the row that reads the disk as the call returns finds the folder and fails |
| AC2 | A refused item is deferred with the rule's name and is carried out by the next event for it; an item whose thing is already missing is marked gone | Drop a refused item back to present; the next event's row finds no deferral record and fails |
| AC3 | With the installation's switch off a call writes due and removes nothing. For a project in report mode it removes only items that carry the owner's confirmation | Ignore the mode; the report-mode row finds the unconfirmed folder gone and fails |
| AC4 | No clock is read to decide a removal: with the fixture clock moved 30 days and no event, nothing changes | Add an age rule for scratch; the clock row finds scratch removed and fails |

### VELDO-0302 Veldo's own creators declare before they create

Components: Clone provisioner, Fleet worktrees, Batch, Sandbox (protected), Receiver's run folders,
Landing line.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each creator's thing has a declared item before it exists and a present item after, with project, ticket, run and lane as owner; the rows cover the clone, the fleet worktree, the run directory, the candidate workspace, the batch clone and the batch's observation folder | Declare after creating; the row that kills the creator between the two finds a folder with no item and fails |
| AC2 | The sandbox's prepare leaves three items: the agent repository, its worktree as the repository's child, and the branch with its start commit | Declare the worktree only; the row finds the agent repository with no item and fails |
| AC3 | A creator that cannot reach the ledger creates nothing and refuses unavailable_service:space_ledger; with no central installation it creates as today | Create anyway on a refused declare; the row finds the folder and fails |

### VELDO-0303 The existing removal paths go through the safety rules

Components: Fleet worktrees, Clone provisioner, Receiver, Landing line. The first seven rows of the table
of 6.10 are the list; the batch and sandbox rows are VELDO-0324.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A fleet worktree is removed through Signal without git's force option; one with an untracked file stays, and the refusal is a deferral on the record | Leave the force option in place; the row's untracked file is lost and the row fails |
| AC2 | A clone's teardown and its failed-provision cleanup go through Signal; the clone_in_use refusal is unchanged; the pins are released after the removal outcome | Leave the direct delete in place; the row with a process holding an open file in the work tree finds the folder gone and fails |
| AC3 | A run directory is removed through Signal, both at the receiver's end and for a leftover the sweep finds | Leave either direct delete in place; the item stays present after its folder is gone and the row fails |
| AC4 | The landing line's candidate folders and the lander's candidate workspace are removed through Signal | Leave the direct delete in place; the same row for a candidate item fails |

### VELDO-0304 The boundary check

Components: Boundary check. It is called from scripts/verify.sh, a protected path (policy.yaml:83), so
the owner's recorded approval is required. It lands after 0302, 0303, 0324 and 0333 (see the build
order).

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The check refuses a creation primitive outside the seam's list | Add a worktree add in a new function not on the list; the check stays green and its mutation row fails |
| AC2 | The check refuses a removal primitive outside the removers and the reviewed list of 6.10 | Restore the forced remove in the fleet module; the check stays green and its mutation row fails |
| AC3 | Every entry of the reviewed list names a function and a reason, and an entry whose function no longer holds a removal primitive fails the check | Accept a list entry that matches nothing; the stale-entry row fails |
| AC4 | The check refuses any function that deletes a folder, a single file or calls a remover and also reads a file's time or compares the clock with a threshold; this rule has no reviewed list | Restore the 30-day branch in prune_times; the check stays green and its mutation row fails |

### VELDO-0305 The run census and the run's space environment

Components: Receiver.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | At each run event every ignored folder git reports in the run's worktree becomes a build output item, whatever its name and depth; a keep entry is left out | Match the name target; the row's folder named otherwise has no item and fails |
| AC2 | An untracked path git does not ignore is never recorded as build output and makes the worktree unique work | Record every untracked folder; the row's new source folder becomes build output and fails |
| AC3 | The run's temporary folder and build variables point at folders declared before the worker starts | Set the variables without declaring; the row finds the build root with no item and fails |
| AC4 | In a worktree reconcile adopted, only folders matching the project's declared patterns are recorded | Apply the ignored-folder rule to adopted worktrees; the adopted fixture's ignored data folder becomes build output and fails |

### VELDO-0306 Docker objects: label, snapshot, events, removal

Components: Docker adapter, Authority service (the poll set). Rows run against a stand-in engine; one
integration row runs against a real one with objects the row itself creates.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An object carrying the run's label or compose project name is an item owned by that run, on the context it was created on | Read one context only; the object on the second context has no item and fails |
| AC2 | An object with no label, no compose project name of a run and no path inside a recorded worktree is a report, is never an item, and is never removed | Attribute it to the only live run; the row with two live runs gives it an owner and fails |
| AC3 | At run finished the run's containers are stopped and removed, then its networks and volumes, each by the engine's non-forced remove; a volume a container of another run still uses is deferred | Remove volumes first; the engine refuses, the item is deferred, and the row that expects it gone fails |
| AC4 | The engine's event stream is a pipe in the service loop's poll set: an engine event is handled with the fixture clock stopped, and end of file on the pipe causes a new snapshot before a new subscription | Read the stream on an interval; with the clock stopped the row's event is never handled and the row fails |

### VELDO-0307 Docker ownership by compose's working folder and by bind source

Components: Docker adapter, Reconciler.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An object whose compose working folder or configuration file label resolves inside a recorded worktree has that worktree as proposed owner; so does a container with a bind mount whose host source is inside one | Match the folder name only; the row whose label names a same-named folder outside every worktree gets an owner and fails |
| AC2 | In report mode such an object is a report showing the proposed owner and is not an item; in act mode it is adopted with the worktree as parent | Adopt in report mode; the report-mode row finds an item and fails |
| AC3 | An object the protect list covers, by its name, its compose project label or its labelled path, is listed as protected and gets neither a proposal nor an item; the rows are a volume, a container and an image | Apply the adoption rule before the protect list; the protected container gets a proposed owner and the row fails |

### VELDO-0308 Run finished, from the receiver

Components: Receiver, Retirement. A review's verdict recorded is VELDO-0337.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Run finished is sent only after the dispatch is conclusive and its group is empty, and the removal is complete before the receiver exits | Send it when the worker's own process exits; the row has a surviving child that keeps a file open under the scratch root (not its working directory), the scratch is judged while the child lives, and the row fails |
| AC2 | At the run's end the receiver runs the census, then Signal, then releases the hold, in that order, and all three are written before it exits | Exit after Signal without releasing the hold; the row's waiting unit, which needs the released hold as well as the freed bytes, is still waiting after the receiver has gone, and the row fails |
| AC3 | When a pending retirement's obligation completes and the retirement is carried out, the dispatch's deferred items are retried in that call; a sweep that finds the obligation unchanged retries nothing | Retry on every sweep call; the row counts retries over three sweeps with an unchanged obligation, finds three and fails |

### VELDO-0309 The gate's space steps

Components: Gate script template, Gate space helper. Both protected: the owner's recorded approval is
required, and the helper is added to the protected paths in the same change. This ticket changes
engine/scripts/verify.sh and this repository's own scripts/verify.sh. Other existing repositories are
VELDO-0325.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | In a repository with no gate_host.json, the need step runs before the first check: in act mode with too little space the answer is GATE: NOT STARTED with the numbers, exit 75, no stamp and no event; in report mode the numbers are printed and the gate runs | Put the need step in the gate host; the fixture repository without the host file starts its checks and the row fails |
| AC2 | A failed gate whose output holds the no-space error on a pool under its floor writes no stamp and no event and answers GATE: NOT JUDGED, exit 75 | Classify after the stamp is written; the row finds a red stamp and fails |
| AC3 | Verdict recorded is sent after the stamp and never before; the gated worktree's build folder is gone and its evidence present before the gate script exits; a gate killed before its stamp sends nothing | Send it before the stamp; the row that kills the gate between the two finds the build folder gone with no verdict and fails |
| AC4 | With no central installation, or space management off, the gate runs and stamps exactly as before the change | Require the ledger; the adopter fixture with no installation goes red and the row fails |

### VELDO-0310 Landed and contained, from the landing station

Components: Landing.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Landed is sent after the completion receipt is recorded and never before | Send it when the landing starts; the row that fails the landing after that finds the worktree gone and fails |
| AC2 | At landed the unit's worktree is removed after its build output, its branch is kept and marked contained, and its image tags go | Remove the branch with the worktree; the row finds no branch and fails |
| AC3 | Every other recorded branch of the project that has moved past its start commit and that the new trunk tip contains is marked contained and its worktree removed; a branch still at its start commit is left | Drop the start commit test; the row's fresh worktree on a new branch is removed and the row fails |

### VELDO-0311 Git hooks: worktrees and landings made with plain git

Components: Git hooks, Event spool, CLI. The hooks record and return. What follows a landing event is
VELDO-0323; installing the hooks is VELDO-0329.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A worktree added with plain git in a bound or plain repository has an item, with its branch, start commit and the owner its branch pattern gives, when the git command returns | Record only through the CLI's record verb; the row that uses plain git finds no item and fails |
| AC2 | Switching a recorded worktree from branch X to branch Y with plain git updates the item's branch to Y and its start commit to Y's commit; a later landing that contains X leaves the worktree in place | Record at worktree add only; the row lands X after the switch, finds the worktree due, and fails |
| AC3 | A committed change of the trunk or of a declared landing ref, made with plain git, leaves one event record with the repository, the ref, the old and the new commit, and the git command returns with nothing removed. The row holds every remover on a fixture latch and the git command still returns | Remove inside the hook; with the remover held on the latch the row finds the git command still waiting and fails |
| AC4 | With the authority not reachable the git command's result is unchanged, the record or event is in the spool, and it is replayed in order at the next CLI call that reaches the authority and at service start before reconcile | Drop the event when the authority is down; after service start the row finds the worktree with no item and fails |

### VELDO-0312 Ticket ended, project ended and worktree abandoned

Components: Authority service, API.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each of the four existing transitions (item complete, item cancel, unit dispose_unit, assignment dispose with ruling close) sends ticket ended after its command commits; one row per transition | Leave the assignment's close unwired; that row's scratch stays present and the row fails |
| AC2 | A project's cancel and complete each send project ended, which ends the items of the project that have no ticket as well as those that have | Send it for complete only; the canceled project's worktree stays with no due record and the row fails |
| AC3 | A command that is refused, or a transaction that rolls back, sends nothing | Send from inside the transition before the commit; the row that rolls the command back finds items due and fails |
| AC4 | Worktree abandoned is sent when a ticket's next run is provisioned in another worktree and when the owner presses Abandon; a month without activity sends nothing | Send it for a worktree unchanged for 30 fixture days; the row finds it due and fails |

### VELDO-0313 The CLI's space verb and the run wrapper

Components: CLI.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | space run declares the run with its station, scratch root, label and compose project name, starts the command in its own containment group, and after the command and the group end runs the census, run finished and release before it exits | Skip the census; the build folder the command made has no item, stays, and the row fails |
| AC2 | space run exits with the command's own status. In act mode with too little space it exits 75 with the numbers and does not start the command; in report mode it prints the numbers and starts it | Start the command anyway in act mode; the row finds the command's marker file and fails |
| AC3 | record and event refuse an unknown kind or event type, a path outside every known root and a path on the protect list, each by name; the event types are ref changed, session started, session ended and released | Accept any path; the row that records a folder outside the roots gets an item and fails |
| AC4 | With no central installation each verb says so, and space run runs the command unchanged | Refuse to run; the row's command never starts and the row fails |

### VELDO-0314 Session hooks

Components: Session hooks. The hooks record and return. The removal that follows is VELDO-0323; installing
the hooks is VELDO-0329.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The SessionStart hook leaves a session started event and a scratch item owned by the session id and the project or plain repository of its working folder, with the session's process id and start time | Record at SessionEnd only; the row for a session that never ends finds no item and fails |
| AC2 | A session started in a folder inside no project and no plain repository leaves the same item with the owner no project, and the ledger refuses that owner for any kind but session scratch | Drop the record when no project matches; the row finds no item and fails |
| AC3 | The SessionEnd hook leaves one session ended event and returns with nothing removed, inside the client's hook time limit. The row holds every remover on a fixture latch and the hook still returns | Remove inside the hook; with the remover held on the latch the row finds the hook still running at its time limit and fails |
| AC4 | A hook that fails or cannot reach the authority spools its record and the session starts or ends as it would without the hook | Let the hook's failure reach the client; the row with the authority down finds the session refused and fails |

### VELDO-0315 Reconcile at start and on demand

Components: Reconciler, Authority service.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each row of the table in 8.8 gives its result, including the agent repository, the build root folder named for a worktree, the plain repository and the session scratch | Adopt every folder under a root; the row with no provable owner gets an item and fails |
| AC2 | Reconcile completes a removing item and marks a missing one gone, and removes nothing else that was not already due | Remove reported things; the reported fixture folder is gone and the row fails |
| AC3 | The service replays the spool and reconciles before it accepts its first dispatch, and a failed reconcile is reported by name while everything else is served | Reconcile in the background; the row that sends a dispatch at once is admitted against an empty ledger and fails |
| AC4 | Nothing runs reconcile on a schedule: the only callers are service start, the API action and the CLI. The row advances the fixture clock by a year with no event and counts one reconcile | Add a periodic call with any period; the row counts more than one and fails |

### VELDO-0316 Admission by pool, need, hold and floor

Components: Admission, Runner, Dispatch contract.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A run is admitted only when free space minus what others hold is at least its need plus the floor; the rows are the boundary values on both sides | Ignore the floor; the row between need and need plus floor is admitted and fails |
| AC2 | In act mode a unit that must wait has no dispatch record, no slot, no reservation and no deadline, and the factory loop's pass lists it under waiting with its numbers and not under refused. What judges it again is VELDO-0334 | Ask admission at acceptance; the row finds a prepared dispatch holding a slot while it waits and fails |
| AC3 | In report mode the same unit is prepared and started, and its hold is recorded as advised with the numbers | Block in report mode; the row's unit is left waiting and the row fails |
| AC4 | The need comes from the project's space file, else from the last five finished runs of the project and station once there are five, else from the pool default; the contract's space field carries it and is covered by the contract digest | Use measured sizes after one run; the row with a single small run is admitted too early and fails |

### VELDO-0317 A dispatch that ends on a full pool is an environment failure

Components: Receiver, Admission. The gate's half is VELDO-0309 AC2.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An unsuccessful end with the no-space error in its output and free space under the floor is environment_failure:no_space: no failed attempt charged, the unit back behind admission | Charge the attempt; the row finds the unit's attempt count raised and fails |
| AC2 | The error with free space above the floor is unknown_outcome:no_space_unconfirmed and is repeated once; a test that prints the error text and then fails for its own reason ends red on the repeat | Treat the text alone as an environment failure; the row's failing test never records its red and fails |
| AC3 | The worktree of a run that ended this way is kept with its uncommitted changes, and the next brief for the ticket says so | Remove the worktree at run finished; the row finds the edit lost and fails |
| AC4 | Two environment failures in a row for one unit raise an andon and stop the repeats | Repeat without a bound; the row counts a third attempt and fails |

### VELDO-0318 The owner decides what becomes of unique work at a ticket's end

Components: Signal, Removers (discard), Ledger (the effects). Depends on 0327 for the touchpoint. Review
worktrees are VELDO-0336, VELDO-0340 and VELDO-0342. The kept branch Discard makes for a detached worktree
is VELDO-0343.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A worktree deferred for unique work at ticket ended, project ended, worktree abandoned or released by its creator, and a worktree owned by a run that is not a review deferred at run finished, raises one request on the space disposition touchpoint with the three answers and the list of files; a later event for the same item raises no second one | Raise a request at every event; the row counts two requests and fails |
| AC2 | Save commits the changes on a kept branch named for the ticket, or for the owning run when the worktree has no ticket, authored as the owner's configured identity, and then removes the worktree without force. Without a settled Save answer Veldo makes no commit | Commit at the deferral; the row finds a commit with no settled answer and fails |
| AC3 | Discard removes that one worktree with git's force option, only on a settled discard answer, only while the file list equals the list shown and rules 1, 2, 3, 4 and 6 pass; the branch and its commits are still there afterwards, and no commit is lost (VELDO-0343) | Skip the list comparison; the row that adds a file after the request was shown loses it and fails |
| AC4 | Keep sets the item to kept; no later event retries it and no second request is raised until the owner presses Abandon | Leave a kept item deferred; the next event's row raises a second request and fails |

### VELDO-0319 The console's Space screen

Components: API, Console.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The usage table's figures per project, ticket and kind equal the sums of the fixture's item records, with each plain repository and "No project" as rows of their own | Sum only present items and leave out deferred ones; the totals row fails |
| AC2 | Pending removal lists every due and deferred item with its reason in words, its retry event and its open decision request; Removed lists every removal with its event, size and free space before and after | Hide deferred items; the row that expects the in-use folder finds nothing and fails |
| AC3 | Reconcile, Adopt, Abandon, Confirm, Wrong and the mode switch are signed owner commands; a session without the owner's passkey is refused each | Accept Abandon as a plain read route; the unsigned row succeeds and fails |
| AC4 | A waiting run, and in report mode a run that would have waited, shows need, free, held and floor on the runs list and the Pools section, and the screen updates from the record stream without a reload | Poll on an interval; the row that stops the fixture clock sees no update and fails |

### VELDO-0320 Migration: report mode and Confirm

Components: Reconciler (mode), Console (Confirm). Depends on 0315, 0319 and 0331. The switch to act is
VELDO-0332.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | For a project in report mode a reconcile over a fixture with 20 worktrees, their build folders, an agent repository and labelled Docker objects adopts them and removes nothing | Act on due items in report mode; the row finds a folder gone and fails |
| AC2 | Confirm for one project and kind removes exactly that group's due items, through all seven rules | Confirm everything pending; the other project's folder is gone and the row fails |
| AC3 | A confirmed item that a rule refuses stays, deferred with the rule's name, and the rest of the group is removed | Stop the group at the first refusal; the row's second removable folder is still there and the row fails |
| AC4 | The confirmation stands through a deferral: while the project is still in report mode the deferred item's next event removes it without a second Confirm, and an unconfirmed item at the same event stays | Drop the confirmation at the deferral; after the holding process exits and the next event runs, the row finds the folder present and fails |

### VELDO-0321 The ledger answers an outside cleaner, and the retirement check

Components: CLI (covers), Ledger. The outside cleaner on the measured host is the nightly script.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | covers answers, for each path it is given, whether an item holds it, the item's state, and "keep" when the item is deferred, kept or protected, or when the path is on the protect list | Answer by presence only; the row with a deferred folder is told it may be removed and fails |
| AC2 | The retirement check lists the cleaner's candidate paths with its age and size tests off, passes only when every one is a ledger item, and names the class of a path that is not | Use the cleaner's own dry run with its filters on; the row's uncovered folder made today is not listed, the check passes and the row fails |
| AC3 | The check fails while any one of the cleaner's five path classes maps to no kind; one row per class | Leave the build root rule out; the row for folders under the cache folder passes and fails |

### VELDO-0322 Scaffold and documents

Components: Scaffold, documents.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | init lays .veldo/space.yaml in a new project, with every key of 6.8 present and commented | Leave the file out of the scaffold; the row that runs init finds no file and fails |
| AC2 | docs/setup.md and docs/installation.md describe the space section, the project file, the hooks and the run wrapper, and pass the docs check | Write a project name into either document; the docs check row fails |
| AC3 | docs/runbook.md gains the situations "the disk is full or a run is waiting for space" and "a worktree is waiting for the owner's answer", and passes the docs check | Name the measured host's project in the runbook; the docs check row fails |

### VELDO-0323 Hook events: the event record, the consumer and the space worker

Components: Ledger (event, consumed), Event consumer, Space worker, Authority service. Depends on 0301
and 0311.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A ref changed record for the trunk or a declared landing ref is consumed on the journal advance that wrote it: with the fixture clock stopped, the worktree of a recorded branch that moved past its start commit and that the recorded new commit contains is removed, build output first, and its branch is kept and marked contained | Consume on an interval; with the clock stopped the worktree stays and the row fails |
| AC2 | The containment tests and the removal both run in the space worker, a child process whose pipe is in the service's poll set: the service process runs no git command for an event record, and while a remover is held on a fixture latch the service answers another packet | Compute containment in the consumer; the row that counts git calls made by the service process for a repository with a hundred recorded branches finds a hundred and fails |
| AC3 | Records are consumed oldest first, one worker at a time, each exactly once; spooled records are consumed at service start before reconcile | Consume without marking; after a restart the row counts two Signal calls for one record and fails |
| AC4 | A session ended record removes that session's scratch. A session started record removes the scratch of every session recorded on the host whose recorded process is gone, in any project and in none, and leaves a session whose process is alive, however old | Look only at sessions of the same project; the crashed no-project session's scratch stays and the row fails |

### VELDO-0324 The batch clone and the sandbox launcher's scratch go through the safety rules

Components: Batch, Sandbox (protected, the owner's recorded approval is required), Removers. Depends on
0302.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A batch's discard removes its clone and its observation folder through Signal; a refusal is a deferral on the record and never an ignored error | Leave the direct delete in place; the row with a process holding an open file in the clone finds the folder gone and fails |
| AC2 | Under a recorded run the sandbox launcher declares its scratch as a child of the run's scratch root and deletes nothing itself; the scratch is removed at the run's run finished, including directories the confined process left unreadable | Leave the launcher's own delete in place; the scratch folder is gone while its item is still present, and the row fails |
| AC3 | The stale scratch pass does not exist: a scratch folder two fixture days old whose lock is free stays when a launcher starts, with an installation and without one | Leave the stale pass on where no installation exists; the row without an installation finds the two-day-old folder gone and fails |
| AC4 | With no space environment the launcher otherwise behaves as before the change: it starts its run, and it removes its own scratch at its own end | Require the ledger; the adopter fixture with no installation fails to start its run and the row fails |

### VELDO-0325 The space steps in an existing project's gate script

Components: CLI (space gate-check), Reconciler, documents. The change to each project's own gate script is
that project's spec, made from the recipe this ticket writes, and is approved by the owner there.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | space gate-check says, for a project's gate script, whether the need call is before the first check, the classify call before the stamp and the verdict call after it; a fixture script laid before the change fails the check by naming the missing calls | Look for the helper's name anywhere in the file; the fixture with the verdict call placed before the stamp passes and the row fails |
| AC2 | Reconcile lists every bound project whose gate script fails the check under space.reports, and a project leaves the list when its script passes | Check the engine's template only; the adopter fixture whose gate script predates the change is not listed and the row fails |
| AC3 | A gate script that predates the change, run through the run wrapper, is admitted before it starts and has its build output removed at run finished | Skip the census for a wrapped gate; the row finds the build folder present after the gate and fails |
| AC4 | docs/setup.md holds the recipe for adding the three calls to an existing gate script, names no project, and passes the docs check | Name the measured host's project in the recipe; the docs check row fails |

### VELDO-0326 Host principals for space commands

Components: Host principals, Ledger, CLI. Depends on 0297.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Installing the service makes the keys of space-observer and space-runner and enrolls both; a hook's command signed as space-observer is accepted without the owner's key being readable by the hook | Sign hook commands with the owner's key; the row that runs the hook with the owner's key unreadable finds no record and fails |
| AC2 | space-observer may sign declare and confirm for a worktree, a branch and session scratch, rebranch, event and the read behind covers, and is refused every other ledger command by name | Accept signal from space-observer; the row that sends it gets items marked due and fails |
| AC3 | space-runner may also sign measure, hold, admit, release, signal and outcome, only for the run or gate it declared | Let it signal for any owner; the row that signals for another run's items gets them due and fails |
| AC4 | Adopt, Abandon, Confirm, Reconcile, marking a proposal wrong, the mode switch, a protect list change and an answer to a space disposition request are refused from both host principals | Accept Abandon from space-runner; the row that sends it finds the worktree due and fails |

### VELDO-0327 The space disposition touchpoint

Components: Settlement journey. It adds one entry to the journey configuration of
control_request_settlement.py. It changes none of the five entries that exist, and it changes neither the
ruling set of authority_contract.py nor the choice map of control_channel_presentation.py.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The journey has a touchpoint space disposition, presented as a decision and answered by the project owner. Its request for one worktree offers exactly three choices, the picks accept save, accept keep and accept discard (a review group's request adds the member picks of VELDO-0342); each settles with the ruling approve, and the effect record carries the choice | Offer the bare words save, keep and discard; none maps to a ruling, the channel does not present the request, and the row that waits for the presentation fails |
| AC2 | The request's terms state that Discard cannot be undone and hold, for each worktree, the list of files it would lose and, for a detached worktree with commits no ref holds, the name of the kept branch those commits go to. The presentation shows both, and the Ledger raises no request that offers the discard pick without that list. The control path has no tier field and none is added | Raise the request with an empty list; the row that reads the presentation finds discard offered with nothing listed and fails |
| AC3 | The effect is applied once, in the settlement's own transaction, from the recorded choice; an answer naming a choice that was not offered is refused as unmatched_choice, and an answer that does not bind the current presentation settles nothing | Read the ruling and not the choice; the row that answers accept keep finds the worktree saved or discarded and fails |
| AC4 | The five existing touchpoints, their rulings and their effects are unchanged, and authority_contract's ruling set still has three members | Add save, keep and discard to the ruling set; the row that reads the set finds six and fails |

### VELDO-0328 Images: built tags are removed, pulled images are kept

Components: Docker adapter.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An image tag a run built is an item owned by that run's ticket and is removed at landed and at ticket ended by the engine's non-forced remove on the tag; a tag a container still uses is deferred | Remove by image id; the row whose image carries a second tag of another ticket loses that tag and fails |
| AC2 | An image a run pulled is recorded once per engine as kept, has no ending event, and is still present after its run's ticket ended | Record a pulled image as an item of the run that pulled it; the row finds it removed at ticket ended and fails |
| AC3 | An image whose name is on the protect list gets no item on either engine context, even when a run tags a build with that name | Check the protect list on the first context only; the row on the second context gets an item and fails |

### VELDO-0329 Installing the git hooks and the session hooks

Components: Git hooks, Session hooks, Reconciler.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Binding a repository, and naming a plain repository, installs both git hooks in the repository's shared hooks folder, or in the hooks folder the repository configures, and keeps an existing hook's own lines | Overwrite an existing hook file; the fixture's own hook line is gone and the row fails |
| AC2 | The session hooks are installed in every client account folder the installation names | Install in the first account folder only; the row that starts a session under the second finds no item and fails |
| AC3 | Reconcile reports a bound or plain repository whose hook is missing, and a named account folder whose session hooks are missing | Report nothing for a missing hook; the row that deletes the fixture's hook finds an empty report and fails |

### VELDO-0330 The rule order, the ledger rule and the protect rule

Components: the rule order of section 7. Depends on 0299.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The rules run in the order of section 7 and the first refusal names the deferral | Run unique work before protect; the protected worktree with an edit is deferred as unique_work and the row fails |
| AC2 | Rule 1 refuses a thing that is not the item recorded: a path that now resolves elsewhere through a link, a folder replaced by another repository's worktree, a Docker name now held by another object id | Compare the locator's text only; the row replaces the folder with a link, finds the link's target removed, and fails |
| AC3 | A locator at or above a protect entry, or with one beneath it, is protected, and no event, no Confirm and no Discard removes it | Skip the protect rule in the discard remover; the row's protected worktree is removed on a discard answer and fails |

### VELDO-0331 Mode per project

Components: Ledger (the mode record), Signal, Admission, Reconciler. Depends on 0297.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each project, each plain repository and no project has its own mode, kept as a ledger record; a scope with no record is in report mode; the record's history holds every switch with the owner's command | Keep one mode for the installation; the row with project A in act and project B in report finds B's due folder removed and fails |
| AC2 | Signal, admission and reconcile's adoption rule each read the mode of the scope the item or the run belongs to: on one pool a run of an act-mode project waits where a run of a report-mode project is advised, and the advised hold still counts as held | Leave advised holds out of what is held; the act-mode row is admitted into space an advised run was promised and fails |
| AC3 | A switch back to report is accepted at once, and from then that project's events write due and remove nothing | Refuse the switch back; the row that sends it stays in act and fails |

### VELDO-0332 Wrong proposals and the switch to act

Components: Ledger (reject, mode, the wrong-proposal record), API, Console. Depends on 0331 and 0320.
The two other conditions of the switch are VELDO-0339.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Marking a proposal wrong writes one record with the scope, the subject, the owner's reason and the day in the installation's time zone. A due item goes to kept and leaves its Confirm group, an adoption becomes a report with no owner, a proposed Docker owner is dropped | Leave the marked item in its group; the row that confirms the group afterwards finds the marked folder gone and fails |
| AC2 | The switch to act for a scope is refused until its three calendar days before today were each a clean report day and no wrong mark is dated today; the refusal names the day that failed and why. A mark on day 2 restarts the count | Count days without reading the wrong-proposal records; the row with a mark on day 2 is switched to act on day 4 and fails |
| AC3 | A day with no event, Signal call or reconcile for the scope is not clean: three idle days do not allow the switch | Count every day in report mode as clean; the row with three idle days is switched to act and fails |
| AC4 | The three days are read from the records when the owner sends the command, and nothing switches a mode by itself: with the fixture clock moved thirty days and no command, every scope is still in report mode | Switch to act by itself once three clean days exist; the clock row finds a scope in act with no owner command and fails |

### VELDO-0333 The gate's leg-time store loses its removal by age

Components: Gate leg timing (protected, policy.yaml:54-55; the owner's recorded approval is required). The
synced copy under scripts/ changes with the canon.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A leg-time file older than 30 fixture days whose authority checkout exists stays when a gate writes its timing | Leave the age branch in prune_times; the row finds the old file gone and fails |
| AC2 | A leg-time file whose authority checkout is gone is still removed at a gate's own write, and the file just written never is | Drop the whole function; the row finds the file of the missing checkout present and fails |
| AC3 | prune_times reads no file time and no clock and leaves a .pending- file alone; its description, the module text and the line a gate prints name the missing checkout only; the canon and the synced copy under scripts/ agree | Change the canon alone; the row that reads the synced copy finds the age test and fails |
| AC4 | read_resources still ignores a resource measurement older than 30 days, under a constant whose name says it bounds a read, and deletes nothing: the old file is there after the read | Delete the constant with the age branch; the row's 31-day-old measurement is returned as current and the row fails |

### VELDO-0334 A unit waiting for space is judged again only after space was freed

Components: Admission, Ledger, Authority service (the wake source space). Depends on 0316.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Admission requested is sent once, when a hold first would wait: a waiting unit offered on three more passes, one of them woken by the account-reset timer, causes one Signal call in all | Retry the deferred items on every admit call; the row counts four Signal calls and fails |
| AC2 | A waiting hold is judged again only when its freed mark is set. On a pass woken by any other source admit returns the recorded answer and reads no free space: with space freed by hand on the fixture pool and a pass woken by the account-reset timer, the unit is still waiting | Read free space on every admit call; the row's unit is admitted on the timer-woken pass and fails |
| AC3 | A removal outcome with freed bytes on the pool, a released hold on the pool and a reconcile each set the mark and raise the wake source space; with the fixture clock stopped, a unit waiting on the pool is prepared after a removal frees enough, with no other action | Set the mark and leave out the wake; with the clock stopped no pass runs, the unit stays waiting and the row fails |

### VELDO-0335 Released by its creator

Components: Ledger (the event command), CLI (event), Event consumer, Space worker. Depends on 0323 and
0326.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A released event signed as space-observer, naming a worktree and an agent repository the record verb declared, removes both through all seven rules, the worktree first; the CLI call returns with nothing removed | Send worktree abandoned from the script; the Ledger refuses an owner action from a host principal, nothing becomes due, and the row finds both folders present and fails |
| AC2 | The Ledger refuses a released event that names an item a Veldo seam declared, or a path with no item, by name | Accept released for any item; the row that names a fleet worktree finds it due and fails |
| AC3 | A released agent worktree whose branch the shared repository does not hold is deferred as unique work, raises one decision request, and is not deleted, with or without a force flag on the script's command | Let the script's force flag reach the remover; the row's unlanded commit is lost and the row fails |

### VELDO-0336 A worktree a run owns

Components: Git hooks, Kind registry, CLI (the run wrapper). Depends on 0311 and 0313.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A worktree added detached with plain git inside a wrapped run is recorded with that run as owner, a review worktree when the run's station is review, and is removed at the run's run finished by git's non-forced remove, after its build output | Record it with the project as its only owner; the row finds the review worktree present after run finished and fails |
| AC2 | A worktree added on a branch inside a wrapped run keeps the owner its branch pattern gives and is still there after run finished | Give every worktree made inside a wrapped run to the run; the row's ticket worktree is removed at run finished and fails |
| AC3 | A review worktree with an untracked file git does not ignore is removed at run finished with no decision request and no force option; the file is deleted first, as review scratch | Defer it as unique work; the row finds the worktree present and a request raised and fails |
| AC4 | Review scratch is removed path by path under rules 1, 2, 3, 4 and 6, with no force option and no clean command: a stray file a live process holds open keeps its worktree, deferred as in_use, and a stray link is deleted without its target being touched | Follow the link; the row's target file outside the worktree is gone and the row fails |

### VELDO-0337 A review's verdict recorded

Components: Receiver (the review station).

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A review's receiver sends verdict recorded when the review's verdict is recorded, and never before | Send it at the review's start; the row finds the review's build folder gone before the verdict and fails |
| AC2 | At a review's verdict recorded its build output and scratch are removed and its evidence folder stays, with the caches the project declares dropped | Remove the evidence folder with the scratch; the row finds no evidence and fails |
| AC3 | A review that ends with no verdict sends run finished and no verdict recorded | Send verdict recorded at every end of a review; the row that kills the review finds a verdict recorded event with no verdict in the store and fails |

### VELDO-0338 Declarations: the project's space file

Components: Declarations reader.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A project with no space file gets every default of 6.8 and is not refused | Require the file; the fixture project without one is refused and the row fails |
| AC2 | An unknown key in a project's file is refused by name | Ignore unknown keys; the row whose file misspells the keep key is accepted, the census records the folder it meant to keep, and the row fails |
| AC3 | A project's protect entries add to the installation's and cannot remove one | Let the project list replace the installation list; the installation's protected volume pattern is gone from the result and the row fails |

### VELDO-0339 What else the switch to act requires

Components: Ledger (mode), CLI (space gate-check), API, Console. Depends on 0332 and 0325.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | With three clean days and one unconfirmed pending group the switch is refused and names the group by scope and kind with its count; after Confirm or Wrong on it the switch is accepted | Read only the day records; the row with an open group is switched to act and fails |
| AC2 | A confirmed item that a rule deferred does not block the switch, and neither does an open adoption or a proposed Docker owner | Count every due or deferred item as unconfirmed; the row whose only pending item is confirmed and in use is refused and fails |
| AC3 | For a bound project the switch is refused while its gate script fails the gate check, and the refusal names the missing call; a plain repository and no project are not asked | Skip the gate check; the fixture project whose gate lacks the verdict call is switched to act and fails |
| AC4 | space.modes and the Modes section show each scope's unconfirmed groups with their counts and the state of its gate, and the history of a switch to act records what was checked | Leave the groups out of the read; the row that expects the open group beside the Act button finds none and fails |

### VELDO-0340 Unique work in review worktrees: one request per day

Components: Ledger (the review group record), Signal, Removers (discard). Depends on 0318, 0327 and 0336.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Two review worktrees with tracked edits deferred on one day raise one request; a third on the next day raises a second, and the first day's request is unchanged | Raise one request per worktree; the row counts two on day 1 and fails |
| AC2 | A later deferral of the same day publishes a new version of the day's request, and an answer bound to the earlier presentation settles nothing. The clock opens and sends nothing: with the fixture clock moved a day and no deferral there is no new request | Add the worktree without a new version; the row's answer to the old presentation settles the group, the worktree the owner never saw included, and the row fails |
| AC3 | A group pick applies to every member still in the group and closes the group. Save commits each worktree's changes on a kept branch named space-saved and the review run's label and removes it without force; Keep sets each to kept; Discard removes each member whose file list equals the list shown and defers a changed one again, into a new group (VELDO-0342 AC3) | Skip the comparison per worktree; the row adds a file to one member after the request was shown, loses it and fails |
| AC4 | Only a review run's worktree is treated this way: a detached worktree owned by a run of another station keeps its untracked file at run finished and raises a request of its own | Treat every run-owned worktree as a review worktree; the builder's untracked file is deleted and the row fails |

### VELDO-0341 Protected Docker objects, by name and by compose label

Components: Probes (the protect list), Docker adapter, Reconciler. Depends on 0296 and 0330.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An object is protected when its name matches a pattern or its compose project label equals a protected project name, either one, on every engine the installation names; the rows are a volume matched by name with no label and a container matched by label under another name, each on two contexts | Test the name only; the row's container named otherwise gets an item and fails |
| AC2 | A container that mounts a protected volume or path is protected, and so are the image it was made from and the networks it is attached to; a container that only runs an image whose name is protected is not | Protect every container of a protected image; the row's run container made from that image is still there after run finished and the row fails |
| AC3 | A protected object has no item, no proposed owner and no Adopt action, and is in no pending group and no decision request, in report mode and in act mode; a Confirm, a discard answer and a released record that would reach one remove nothing | Read the list at removal only; the row's protected volume shows under Reports with a proposed owner and fails |

### VELDO-0342 Review groups: an answer for one worktree, and a second group on the same day

Components: Ledger (the review group record), Signal. Depends on 0340.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A group's request offers the three group picks and, for each member, the three member picks with its index. In a group of three the answer accept discard w2 discards only member 2 and settles the request, and the Ledger raises a new request for members 1 and 3 on the same group record; an answer to the settled request is refused as request_closed | Apply a member pick to the whole group; the row finds member 1 discarded and fails |
| AC2 | When the group picks and the member picks of every member do not fit one message part, the request offers the group picks and the member picks of the lowest indexes that fit, and its text names the members without a pick; after a member pick the next request offers picks to the members after them | Offer every member pick whatever the size; the presenter refuses to render and the row that waits for the presentation fails |
| AC3 | A scope has at most one open group per day: while one is open a deferral joins it. After the day's group is closed by an answer, a deferral the same day opens a new group with the next sequence number and its own request | Reuse the day key; the row's command is refused as a duplicate entity and the worktree has no request |

### VELDO-0343 Discard keeps every commit

Components: Removers (discard), Ledger. Depends on 0318; the group answers are 0340 and 0342.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Discard of a detached worktree whose checked-out commit no ref holds first creates a kept branch at that commit, named as Save names one, and records it as a branch item in state kept; afterwards the commit is reachable from that branch and the worktree's uncommitted file is gone | Discard without creating the branch; the row finds the commit unreachable and fails |
| AC2 | When the kept branch cannot be created, because the name is taken by a branch that does not hold the commit or git refuses the ref, the discard does not run: the worktree and its files are still there, deferred as remove_refused | Run the remove after the failed branch write; the row finds the worktree gone and the commit unreachable and fails |
| AC3 | Discard of an agent's worktree leaves the agent repository and its branch in place, kept, with every commit on that branch | Remove the agent repository with the worktree; the row finds the branch's commit in no repository and fails |
| AC4 | Creating the kept branch makes no commit and sends no landing event: the row counts the same commit objects and the same event records before and after | Commit the worktree's files in Discard as Save does; the row finds a new commit and fails |

### VELDO-0344 The process reader

Components: Process reader, Probes, Declarations reader. Depends on 0296, 0299 and 0330.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | With no reader at the fixed path, or one that fails a check (not a regular file, an owner other than root, a group or mode other than the installed ones, a capability set other than exactly cap_sys_ptrace permitted and effective, no digest in the installation's space section, a digest other than that one, or a header that says it holds no capability), the probe does not use it, every unread process is judged as before this ticket, and the in_use facts name the reader's state and the check that failed | Skip the digest check; the row puts a program that prints an empty table in the reader's place, the undumpable process in the item is not counted, the item reads free and the row fails |
| AC2 | With the reader in use, a process of the owner's that is not dumpable counts for an item exactly when its working directory, an open file or a mapped file is the item or beneath it: the one in the item holds it, named by process id and fact, and the one outside it no longer counts | Match the working directory only; the row whose undumpable process holds nothing but an open file beneath the item reads free and fails |
| AC3 | A root-owned process a login started is judged by the same facts: in the item it holds it, and elsewhere it does not count. A process with any fact the reader could not read (an x line, no block, or a start time other than the one the probe reads) stays unread and is judged by the bound of VELDO-0299 | Take a block with an unread fact as read; the row's root-owned process, whose descriptors could not be listed and which holds a file in the item, reads free and fails |
| AC4 | The reader takes no argument and reads only the stat, cwd, fdinfo, mountinfo and maps entries of each process. It prints numbers only, in the format of design section 7.1, and its seccomp filter ends it on any call that attaches to a process, signals one, writes to one or opens a file for writing | Allow kill in the filter; the row's patched copy of the reader, which signals itself after the filter is in place, exits normally and the row fails |
| AC5 | An output with no end line, an end count other than the number of blocks, a line outside the format or an exit status other than 0 is not used at all: the reader's state is refused, and every unread process is judged as before this ticket | Use the blocks read before the cut; the row cuts the output before the block of the process in the item, the item reads free and the row fails |

The four cases the owner named, and the row that holds each: the reader absent, fail closed (AC1); the
reader present and an undumpable process of the owner's in the item holds it (AC2); a root-owned
process the owner started holds it (AC3); a tampered reader is refused (AC1's falsifier, and AC5 for
its output).

## 13. Decisions taken in this design

| Decision | Why |
| :- | :- |
| The ledger is records in the existing control store, not a new database | One writer, one journal, one place the console already reads. The volume is hundreds of records a day |
| The library runs inside the process that removes; there is no space daemon | The owner asked for cleanup as part of the process. A run, a gate and a landing station remove at their own events. For hook events the remover is the authority service's worker, started by the event's own record |
| Outside creators are covered by hooks git and the client run themselves, by the gate script, and by one wrapper | An instruction to call the CLI is the builder brief again. A hook runs whether or not anyone remembers it |
| The git hook is the event source for hand landings, and it only records | The lead's decision: a hand landing never removes worktrees inside the git command. The hook writes one record and returns; the service consumes it right after. A landing command that took minutes, or failed halfway through a removal, would be worse than a removal that starts a moment later. The price is that the service must be running, which migration step 1 makes true and which every other part of Veldo already needs |
| The service removes through a child worker, not in its own loop | Deleting a 30 GB build folder takes long enough that a service doing it in line would stop answering packets |
| Session hooks only record too | The client gives a hook a short time limit and the session is exiting. Same pattern as the git hook |
| An existing project's gate gets the steps by its own change | The gate script is each project's own catalog and a protected path there. Veldo reports a gate that lacks the steps and covers it with the wrapper; it does not rewrite another repository's protected file |
| core's gate gets the space steps first, in report mode. Act mode starts for a project only after three consecutive report days with no wrong proposal, by the owner's command. Then the other projects, the same way | The lead's decision (b). Mode is therefore per project, a proposal can be marked wrong, and the Ledger refuses the switch until the three days are in its records. The mode lives in the installation's store, so a project cannot promote itself |
| The switch to act also needs every pending group answered, and the space steps in the project's gate | The lead's decision (d), and the enforcement of (b). An unconfirmed group is a due item the owner neither confirmed nor marked wrong; a confirmed item a rule deferred is answered. Adoptions and proposed Docker owners do not block, because the decision names pending groups and those proposals remove nothing by themselves |
| No removal by age anywhere in Veldo, the sandbox's age pass included | The lead's decision (c). It holds with a central installation and without one. The sandbox's stale scratch pass and the 30-day branch of the gate's leg-time store are deleted, and the boundary check refuses a new one. A killed launcher's scratch on a repository with no installation stays until the owner removes it. The host's nightly script removes by age until its retirement check passes; it is outside Veldo and is the one exception, bounded by section 11 |
| A unit waiting for space is judged again only after a write that frees space | The lead's decision: admission retries are woken by the event that frees space (a removal finishing, a run ending), never by a timer pass. The factory loop offers a waiting unit on every pass, so the rule is enforced inside admit, by a mark only those writes set |
| The Save, Keep and Discard touchpoint is accepted, and its answers are picks | The lead's decision (a). The ruling set is closed in the contract, the channel and the settlement. Three picks under the ruling approve fit it without changing shared code |
| A script gives up its own things with released, not with Abandon | Abandon is an owner action and no host principal may send it. Released is accepted only for things the same kind of script recorded, and goes through all seven rules |
| A detached worktree made inside a wrapped run belongs to the run | A review's checkout has no branch and no ticket. Owned by the project alone it would never end |
| A review worktree's stray untracked files are review scratch, removed at the review's end with no request. Its tracked modifications go into one grouped request per day | The lead's decision (e). A review worktree is tied to a run whose station is review, so a builder's detached worktree keeps its files. The scratch is deleted path by path under the rules, never by a force option, so Discard stays the one forced removal. The day is the day of the deferral event; no clock opens or sends the request |
| One answer covers a day's review group, and the request also offers an answer for one worktree | The lead's decision (f). A group pick answers every member. A member pick, accept with the answer and the member's index, answers one and leaves the rest under a new request. The channel already takes it: a pick names one or more values and a request's choices are any distinct list. When the picks do not all fit one message part, the request offers the group picks and the member picks that fit, lowest index first |
| Discard never loses a commit | The lead's decision (g). A detached worktree's commits are put on a kept branch before the worktree goes, and a discard that cannot make the branch does not run. Only uncommitted changes are discarded. The branch is a ref write, not a removal and not a commit |
| seoeng_cms-postgres-data and docker_minio_data stay on the protect list | The lead's decision (h). Each is protected by exact name. Their compose project names are not added, because docker as a project name is too broad |
| A review group is keyed by scope, day and a sequence number | With the day alone as the key, a worktree deferred after the owner answered that day's group had no group to join and could get no request. One open group per scope and day; an answered group closes and the next deferral that day opens a new one. The day stays a key of the deferral event, and no clock is added |
| Unread processes are read by a separate reader with one file capability, not excused by a list of names and not by a capability on the service | The owner's decision (Telegram 41204 and 41205). A name is whatever a process calls itself, and the re-review excused a renamed process with one. CAP_SYS_PTRACE on the service would let the whole service attach to any process; on a reader that takes no input and is shut in by a seccomp filter it can only read |
| The reader prints device and inode numbers, never paths | Measured: cap_sys_ptrace alone gives the working directory, the maps and each descriptor's inode number, and does not list the descriptors' paths. Numbers are also the same in every mount namespace, where a path is not, and they tell whoever runs the reader no file name. The price is that the probe lists the item's files to compare, 0.3 seconds for a worktree of 9,011 entries |
| The reader is C, static, built like veldo-userns | A file capability needs a binary of its own. The repository already builds, reviews and gates one static C helper, and a second toolchain for 200 lines would be a dependency with no gain |
| The reader's digest is in the installation's space section, and its path is fixed in the probe | The path cannot be pointed elsewhere by a file an agent can edit. Root ownership is what keeps the binary from being changed; the digest refuses a binary that is not the build the owner made |
| Hooks sign as a host principal, never as the owner | A git hook runs in any shell. It may record what it saw; it may not answer for the owner |
| A hook never fails or waits on the service; it spools | A landing or a session must not break because the authority is down |
| Admission is asked before a dispatch is prepared | A prepared dispatch holds a slot and has a deadline |
| Admission double counts on purpose | Free space already reflects what running runs have written, and their unspent hold is subtracted as well. The error is on the safe side and shrinks at each measurement |
| Branches are kept | The owner's request names keeping the branch. A contained branch costs almost nothing, and deleting one is not undone by a rebuild |
| Pulled images are never removed | Nothing in Veldo can prove an image can be pulled again, and one that could not cost a whole run on 2026-11-13 |
| The protect list is matched by name and by compose label, on every engine, and a protected thing is never proposed | The lead's list, complete, and the owner's rule for the places project: not removed and not offered. Two tests because a hand-made object has no label and a renamed one has no matching name. A container is not protected for running a protected image alone, or every gate database made from a common image would stay forever |
| Unlabelled Docker objects are reported, not guessed, in the first release | A wrong guess removes another run's database |
| The one forced removal is the owner's Discard, allowed only after the owner's discard answer | The lead's decision. Everywhere else the tool's own refusal is the last safety check. Here the owner has seen the file list and signed the loss, and every commit is kept |
| Scratch of a session outside every project is recorded under the owner no project | The lead's decision. Leaving it unrecorded would leave the growth the owner named with no owner and no ending event |
| Reconcile may act on a past event | Otherwise an adopted worktree whose ticket landed last month would never be removed. It is bounded to service start and an explicit request |

Left out, each a later ticket if wanted: a second host; build caches shared between worktrees; shrinking a
container engine's disk image; removing contained branches; a per-ticket space budget; a "superseded"
transition; removal of unlabelled Docker objects.

## 14. Validation response

Five validations, all of 2026-11-13, all in the owner's notes repository under research/codex-reviews.
Every point was checked against the code before it was taken. The newest is in 14.5; 14.1 to 14.4 run
from the fourth back to the first and keep their numbers, because other sections cite them.

### 14.1 The fourth validation (design-veldo-0295-validation4-2026-11-13.md)

Three required changes and six smaller ones. All nine are taken. The code and the host agreed with the
validation on every one; three rows say where a citation or a recommendation was adjusted, with the
evidence.

| Point | Checked against the code | Where it is fixed |
| :- | :- | :- |
| E1 decision (d) not carried | True of revision 4: the mode command refused on the days and a wrong mark only. Of the two readings offered, the simplest is taken, as recommended: pending groups are due items, and open adoptions and proposed Docker owners do not block. An item needed a field to say it was confirmed, and the confirmation had to survive a deferral, or a confirmed item in use would block the switch forever | Section 2 (pending group), 4.1 (confirmed), 4.7, 6.1 (confirm group, mode, the definition), 6.6, section 10, section 11 step 8 and the clean day text, section 13; ticket 0339 AC1, AC2 and AC4, ticket 0320 AC4, ticket 0301 AC3; the spec's AC8 |
| E2 decision (e) not carried | True: revision 4 deferred a review worktree with a stray file and raised a request for each. Read on the host: the report and event log go to a folder outside the worktree (codex_review.sh:46, and :135-136, where the validation has :134-135), and the capsules are copied out at :152-154 (the validation has :145-150). The tests mode is at :116-124. On the grouped request the code decides one thing the validation left open: an answer must be among the choices the presentation lists (control_request_settlement.py:509), so one answer covers the group | Section 2 (station, review worktree, review scratch), 4.9, section 5 (two rows), 6.5 (the review scratch remover), 6.9, section 7 (rule 5's exception and "Review worktrees"), 8.5, section 13; ticket 0336 AC3 and AC4, ticket 0340, ticket 0318 AC1, ticket 0298 AC1; the spec's AC2 and AC3 |
| E3 the protect list | True. Read on the host: ~/projects/places holds data and backups folders and a compose file with no project name of its own, so the compose project is places. Read-only listings on both contexts gave the names in section 11. One recommendation is narrowed: postgis/postgis is protected as an image, but a container is not protected for running it, because core's gates make their own containers from the same image | Section 2, 6.6 (space.protected), 6.8, section 7 "The protect list", 8.8, section 10, section 11 (the table); ticket 0341, ticket 0307 AC3, ticket 0296 AC3; the spec's AC3 |
| F1 the boundary check's build order and approval | True: the Replaced paths of 6.10 are on no reviewed list until 0302, 0303, 0324 and 0333 land, and scripts/verify.sh is protected (policy.yaml:83) | Section 12 (build order, the approval list, ticket 0304's header), section 3, the fifth of the six things |
| F2 the 30-day constant has a second reader | True: gate_legs.py:236 reads it in read_resources, and :279 lists .pending- files, which only the age test removed. The constant stays for the reader under a name that says so; a leftover .pending- file stays | 6.10 (the prune_times row), section 3; ticket 0333 AC3 and AC4 |
| F3 the critical tier | True: a search of control_request_settlement.py and control_channel_presentation.py finds neither "tier" nor "critical". The AC is reworded to what the control path carries, the request's terms | Section 7 "Which touchpoint"; ticket 0327 AC2 |
| F4 act while the gate lacks the steps | True: nothing refused it. The mode command now runs the gate check for a bound project | 6.1, 8.2, section 11 step 8; ticket 0339 AC3 |
| F5 ticket 0296 AC2 held two claims | Split | Ticket 0296 AC2 and AC4 |
| F6 the citation of gate_schedule.py | True: the canon is engine/scripts/gate_schedule.py:436 | 6.10, the reviewed list |

Revision 5 also changes two things revision 4 answered in 14.2: the run-owned worktree of C5 now follows
decision (e), and the ticket for C6 no longer names a tier.

### 14.2 The third validation (design-veldo-0295-validation3-2026-11-13.md)

Six required changes and seven smaller ones. All thirteen are taken. The code agreed with the validation
on every one; on four the row says what the code added.

| Point | Checked against the code | Where it is fixed |
| :- | :- | :- |
| C1 decision (b) not carried | True of revision 3: one mode key for the installation, core's gate change after act mode, no record of a wrong proposal. The mode is now a ledger record per scope and not an installation key, because a key in a file could be edited past the Ledger's refusal | Section 2 (scope, mode, proposal, clean report day), 4.7, 4.8, 6.1 (reject, mode), 6.6, 6.7 (Mode), 6.8, 8.2, 8.8, section 10 (Modes, Wrong), section 11 (the order, and what makes a day clean), section 13; tickets 0331 and 0332, 0319 AC3, 0326 AC4 |
| C2 decision (c) not carried | True. agent_sandbox.py:2074-2110 tests age at :2095 against 24 hours (:2047) and is called at :2202. gate_legs.py:267-299 deletes at :292 by the 30 days of :107, and is called at :205 as well as the :263-264 the validation names. A search of the engine for every function that both deletes and reads a file's time finds these two and no third | Section 5, 6.2 (the age rule), 6.10 (both rows), 8.8 (stray launcher scratch is reported), section 13; ticket 0324 AC3 and AC4, ticket 0333, ticket 0304 AC4 |
| C3 admission retries ride every pass | True. offer is at control_service.py:2614 and submits to the runner on every pass; passes are woken by journal, run end, working tree and the account-reset timer (:1595-1596, 3494-3496). Sending admission requested once would not be enough for the lead's wording, because a later admit call that read free space again on a timer-woken pass would still be a retry paced by the timer. So admit judges a waiting hold again only when a freeing write has marked it | 4.3 (retry asked, freed), 6.7, section 7 Retry, 8.1; ticket 0334, ticket 0316 AC2 |
| C4 host cleanup routed to commands nothing may sign | True. The event command took three types, and Abandon is refused from host principals. Read on the host: agent_sandbox.sh:246 removes the script's own half-made prepare, and :476 is its remove command, which checks the shared repository first or takes a force flag. Of the two ways offered, the new observer event is taken, because the remove command runs long after any wrapped run has ended | 4.5, section 5 (released by its creator), 6.1, 6.9, 6.10, 6.11, section 11; ticket 0335 |
| C5 the review worktree is never removed | True. codex_review.sh:55 adds it detached and :51 removes it by force. The hook way is taken, limited to detached worktrees: a builder under the wrapper that adds a worktree on a ticket branch must keep it after its run | Section 5 (the row and its paragraph), 6.9, 8.5, 6.10, section 11; ticket 0336, ticket 0298 AC1 |
| C6 the touchpoint cannot be settled | True in all three places named (authority_contract.py:379 and 414; control_channel_presentation.py:173-175; control_request_settlement.py:509, 571, 670). The second way is taken: three picks, each with the ruling approve (control_channel_presentation.py:176-180, 254-265). An answer outside the three is already refused as unmatched_choice | Section 7 "How three answers fit a closed set of rulings"; ticket 0327 |
| D1 section 15 held decided questions | Taken | Section 13 records (a), (b) and (c); section 15 holds only what is new |
| D2 containment computed in the service loop | Taken | Section 3, 6.9, 8.4, section 9; ticket 0323 AC2 |
| D3 the retirement check's filters | True (nightly_build_cleanup.sh:17-18, 88-91) | Section 11, the retirement check; ticket 0321 AC2 |
| D4 0308 held three concerns | Split | Ticket 0308 keeps run finished and the retirement retry; ticket 0337 is the review's verdict |
| D5 0296 AC1 held two claims | Split, and the ticket with it, to stay at four ACs or fewer | Ticket 0296 (the installation's section, AC1 and AC2), ticket 0338 (the project's file) |
| D6 mutation_ownership.py callers | True: cleanup at :286 and :288, through remove_tree at :200 | 6.10, the table of entries that stay |
| D7 spec | Taken | The spec's AC2, AC3, AC5, AC8, Context, Out of scope and History |

Where each of the lead's decisions is carried:

| Decision | Sections and tickets |
| :- | :- |
| (a) the Save, Keep and Discard touchpoint is accepted | Section 7; tickets 0327 and 0318 |
| (b) core's gate first in report mode; act after three consecutive clean days; then the others | Section 2, 4.7, 4.8, 6.1, 6.6, 8.2, section 10, section 11 steps 6 to 10; tickets 0331, 0332, 0325 |
| (c) no removal by age anywhere in Veldo | Section 5, 6.2, 6.10; tickets 0324, 0333, 0304 AC4, 0301 AC4 |
| (d) the switch to act also requires no unconfirmed pending group | Section 2, 4.1, 4.7, 6.1, 6.6, section 10, section 11; tickets 0339, 0320 AC4 |
| (e) a review worktree's stray untracked files are review scratch, removed at the review's end with no request; tracked modifications go into one grouped request per day | Section 2, 4.9, section 5, 6.5, section 7, 8.5; tickets 0336 AC3 and AC4, 0340 |
| (f) one answer covers a day's whole review group, and the request also allows a per-worktree exception | 4.9, 6.6, section 7 item 4, section 10, section 13; tickets 0342 AC1 and AC2, 0340 AC3, 0327 AC1; the spec's AC3 |
| (g) Discard never loses commits: a detached worktree's commits are kept on a kept branch before the worktree goes, and only uncommitted changes are discarded | 4.9, 6.5, section 7 ("Which touchpoint", the Discard row, item 6), section 13; tickets 0343, 0318 AC3, 0327 AC2; the spec's AC3 |
| (h) seoeng_cms-postgres-data and docker_minio_data stay on the protect list | Section 11 (two table rows and the paragraph under the table), section 13 |
| Admission retries are woken by the event that frees space, never by a timer pass | 4.3, 6.7; ticket 0334 |
| Discard is the one forced removal, only after the owner's discard answer | 6.5, section 7; tickets 0300 AC3, 0318 AC3, 0330 AC3 |
| A hand landing removes nothing inside the git command | 6.9, 8.4, section 9; tickets 0311 AC3 and 0323 |
| Scratch of sessions outside any project has the owner no project | Section 2, 4.1, 8.7, 8.8; tickets 0314 AC2, 0323 AC4 |
| Floors and needs: floor 20 GB, gate 50, builder 16, review 16, measured after five runs, advising in report mode | 6.7, section 11 values; ticket 0316 |
| Unlabelled Docker objects are reported, never removed; compose label and bind source adoption | 6.4, 8.8; tickets 0306 AC2 and 0307 |
| Lead-session scratch by session id, SessionStart and SessionEnd hooks | 6.9, 8.7; tickets 0314, 0323 AC4, 0329 |
| Unique work at a ticket's end: one request, three answers, Veldo never commits on its own | Section 7; ticket 0318 |
| The protect list, complete, by name and by label on both engines, never proposed and never removed | Section 7, section 11; tickets 0341, 0296 AC3, 0307 AC3, 0328 AC3, 0330 AC3 |

One of these is carried more widely than it was worded. The lead's decision on session scratch says a
crashed session's scratch is retried at the next session start on the same project. The design retries it
at the next session start anywhere on the host (8.7). That includes the same project, and it is the only
form of the rule that reaches a crashed session with no project.

### 14.3 The second validation (design-veldo-0295-validation2-2026-11-13.md)

Four required changes and eleven smaller ones. All fifteen were taken in revision 3. On one, S2, the code
led somewhere a little different from what was asked, and the row says how. The rows revision 4 changed
are brought up to date.

| Point | Checked against the code | Where it is fixed |
| :- | :- | :- |
| R1 hand landing removes inside the git command | True of revision 2, and against the lead's decision. The machinery named exists: the local socket client (control_client.py), the journal advance that wakes the loop (control_service.py:1588-1596, 3227). One addition: hint_after wakes the loop only when a factory loop is configured (the test at :1595), so the consumer is called beside that wake and does not depend on it. And a removal inside the service loop would stop the service answering, so the consumer hands it to a child worker on the poll set | 4.5, 6.1, 6.9, 8.4, section 9, section 13; ticket 0311 AC3 (the hook returns with nothing removed) and ticket 0323 (the consumer and the worker). The old open question is gone |
| R2 existing projects' gates | True. scripts/check_template_sync.sh:30 excepts scripts/verify.sh; init_scaffold.py:889-904 never overwrites. Read on the host: core's gate script has 485 lines, seven other bound projects have 159 to 251, none mentions the gate host | Section 3 corrected; 6.9 (two gate rows); 8.2 "Which gates this reaches"; 8.8; section 11 steps 5, 8 and 9; ticket 0325. The validation asked for an AC on 0309; it is 0325 AC2, because 0309 is the template and 0325 is the existing repositories |
| R2 (c) keep the launcher's guard | Taken, and tied to act mode as well: in report mode Signal removes nothing and admission only advises, so the launcher's refusal and delete stay until core is in act mode, which since revision 4 comes after core's own gate change | 6.10 host table; section 11 steps 5 and 9 |
| R3 no-project owner | True: 4.1 and section 2 allowed two owner values while 8.7 recorded a third | Section 2, 4.1, 6.6, 8.7, 8.8, section 10; ticket 0314 AC2, ticket 0323 AC4, ticket 0319 AC1. The catch-up rule is the simplest one offered: every session started looks at every recorded session on the host. The old open question is gone |
| R4 missing removal paths | True, all four. control_batch.py:944-951 with the creators at :530 and :721; agent_sandbox.py:2052-2071 called at :2106 and :2223; control_service.py:894-898 called at :1006 and :1204; plugin_load_runner.py:308-309. Revision 2 had put agent_sandbox.py:2071 on the reviewed list as a same-call temporary folder, which was wrong. One more thing the code shows: the stale scratch pass at :2106 removes by age (more than a day), which is the kind of cleanup this design replaces. Since revision 4 that pass is deleted in every case | 6.10; rule 4; 8.8; ticket 0302 AC1 (batch creators), ticket 0324 (batch discard and the launcher's scratch), ticket 0299 AC4 |
| S1 branch switch | True: post-checkout also runs on a checkout, and revision 2 recorded worktree add only | 4.1 (branch field), section 5, 6.1 (rebranch), 6.9, 8.5, 8.8; ticket 0311 AC2 |
| S2 the decision touchpoint | Partly. control_backlog.py:185 is the wrong touchpoint, as the validation says, and request.py:74-77 has decision choice with the irreversible rule at :92 and :236. But request.py is the vocabulary of request records in a repository. Requests in the owner's inbox are settled by control_request_settlement.py, whose journey (:106-127) has five touchpoints, each with the rulings approve, reject and return for elaboration; no control module names decision choice. So a three-answer request needs a new journey touchpoint. Since revision 4 its three answers are picks under the ruling approve, because the ruling set is closed (14.2, C6) | Section 7 "Which touchpoint"; ticket 0327 (the touchpoint), ticket 0318 |
| S3 signing principal | True (control_client.py:10-23). The service and the receiver already have host principals (control_service.py:951-952) | 6.11; ticket 0326 |
| S4 SessionEnd removes in the hook | True: the pack's hook has a 15 second limit (packs/claude/hooks/hooks.json) | 6.9, 8.7; ticket 0314 AC3, ticket 0323 AC4 |
| S5 space_wait listing | True (control_service.py:2640-2646) | 6.7; ticket 0316 AC2 |
| S6 loose files in the scratch root | Read on the host: the launch scripts write their logs to the owner's notes repository (claude_run.sh:38, codex_run.sh:27-34), not to the scratch root. The loose files there come from sessions' own commands. Nothing proves their owner | 6.9 (the limits), 8.8, section 10: they stay reported with their total size, and Veldo does not remove them |
| S7 who computes contained by another branch | Taken | Section 5, after the event table |
| S8 adopted worktree with no start commit | Taken as recommended | 4.1, section 5 |
| S9 ticket rows | Taken. 0299 was at four ACs, so the rule 1 row went into a new ticket with the rule order and the protect rule (0330). The pulled image has its own ticket with the built tags (0328) | Tickets 0306 AC3, 0328, 0330 |
| S10 git_process.py:144 | True: it points the hooks folder at a private folder | 6.9, first limit |
| S11 nine records | True: the row lists eight things | The spec's AC1 says eight |
| Check 3, Discard keeps the branch | Taken | 6.5, section 7; ticket 0318 AC3 |
| Check 6, build folders adopted by name only | Taken | 8.8, section 11 |

### 14.4 The first validation (design-veldo-0295-validation-2026-11-13.md)

Six blocking and nine smaller changes, all taken in revision 2. The table is revision 2's, with the rows
revisions 3 and 4 changed brought up to date.

| Point | Checked | Where it is fixed |
| :- | :- | :- |
| B1 external creators | True. The launch scripts call plain git and the clients directly; no service runs. One thing the validation did not have: Veldo's guarded git and the host's sandbox script run with hooks off (candidate_git.py:74, agent_sandbox.py:772), so a git hook cannot cover those and the seam must | 6.9, 8.4, 8.5, 8.7; tickets 0311, 0313, 0314, 0323, 0329. The validation offered a service-loop watch or a hook for ref changes. The hook is the source, because it sees the change in the command that made it and loses nothing while the service is down; since revision 3 the service is the remover. Every creator the lead named is a row of 6.9: gates outside gate_host.json, hand-made worktrees, manual landings, lead sessions, builder runs through the launch scripts, the lock queue. Revision 4 adds the two the third validation found still without a source: the review script's throwaway worktree and the sandbox script's own deletes |
| B1 (a) "record before worktree add" | A CLI call a script must make first is an instruction. The post-checkout hook records in the same git command instead, a moment after creation and not before it | 6.9. The CLI's record verb remains for scripts whose git runs with hooks off |
| B2 gate | True. The gate host runs only with a host file (engine/scripts/verify.sh:108), and the gate script writes the stamp (:352-382) | 8.2, tickets 0309 and 0325. The need is read from the project's space file, so gate_host.json does not change. Revision 2 fixed this for new repositories only; revision 3 covers the existing ones |
| B3 removal paths | True for the four named. The search found more: control_clone.py:606, control_launch.py:1397, control_launch_work.py:107, lander.py:538, and a set of same-call temporary folders | 6.10, tickets 0303, 0304, 0324 and 0333. Every path is listed with its file and line and its replacement, the two removals by age included. The same-call temporary folders stay, on a reviewed list the gate enforces, because none can hold a worktree, build output or another run's files; routing them through a ledger would record things that live for one function call |
| B4 rule 5 and agent repositories | True. A worktree's branch always reaches its own tip; prepare makes a private repository the shared one does not list (agent_sandbox.py:779-793) | Section 7 rule 5, the agent repository kind in sections 2, 5, 6.5 and 8.8, ticket 0299 AC2 and AC3, ticket 0302 AC2 |
| B5 waiting dispatch | True (control_dispatch.py:134, 476-495, 520-521) | 6.7, 8.1, ticket 0316 |
| B6 transitions | True. No superseded transition exists. The VELDO-0133 close is the assignment's dispose with ruling close (control_assignment.py:122, 529) | Section 5 event table, ticket 0312. Superseded is dropped, not added. The design uses only transitions that exist. The new things of that sort are each a separate ticket: the settlement touchpoint (0327), the mode switch (0332 and 0339) and the released event (0335) |
| M1 other roots | 13 roots on the host | 6.8 plain repositories, 8.8 |
| M2 build roots | Taken | 6.8, 8.8 |
| M3 rebuild cost | Taken | Section 5, last paragraph |
| M4 retry and sweep | True (control_launch.py:714-722; control_retirement.py:53-56). The same fault came back through admission in revision 3 and is closed in revision 4 (14.2, C3) | Section 7 Retry, ticket 0308 AC3, ticket 0334 |
| M5 Docker stream | Taken | 6.4, ticket 0306 AC4 |
| M6 declare_owners | True; the reservation service does not call it | Section 3, Ledger row |
| M7 canon paths | True. Revision 2 added a false claim here, that the gate script has a synced copy; corrected in revision 3 | Section 3 |
| M8 five classes | True; the script has five find lines | Section 11 and the spec's AC8 |
| M9 absent section | Taken as recommended | 6.8, ticket 0296 AC1 |
| Check 3 additions | Mapped files and stopped containers' bind mounts added; the protect list is explicit | Section 7 rule 4, section 11, ticket 0296 AC3 |
| Check 6 additions | The temporary folder outside the scratch roots stays reported; the nightly script asks the ledger while both run | 8.8, section 11, ticket 0321 |
| Check 7 tickets | Each finding taken: dependencies stated, two-concern tickets split, the race row made deterministic, the idle-run falsifier replaced by a clock advance | Section 12 |
| Q1 to Q4 | Decided by the lead as the validator recommended | 6.7 and section 11; 6.4 and ticket 0307; 8.7 and ticket 0314; section 7 and ticket 0318. The table in 14.2 lists them with the later decisions |

One thing found while fixing B1 that neither revision 1 nor the validation had: a branch that has not
moved past its start commit is reachable from the trunk the moment it is made. Without the start commit
rule of section 5, the first landing after a worktree is added would remove it.

Four claims not checked. That the channel presents three picks as three offered choices of one request:
the pick form exists and maps to approve, but its one use today (a project proposal) was not traced to
the presentation, and ticket 0327 AC1 is where it is proved. That an open request can be published again
under a new version when a worktree joins its group: the version is checked at settlement
(control_request_settlement.py:507), but no caller that raises the version of an open request was
traced, and ticket 0340 AC2 is where it is proved. That compose writes its working folder and
configuration file labels on both of this host's engines: revision 5 ran read-only listings of volumes,
containers and images for the protect list, which show the compose project label on both, and no other
Docker command; ticket 0307 has the builder check the other two labels. That the client runs its
SessionEnd hook on every ordinary exit: the pack has only a PreToolUse hook today, and ticket 0314's
rows are where it is proved; a session whose end hook does not run is caught at the next session start,
like a crash.

### 14.5 The fifth validation (design-veldo-0295-validation5-2026-11-13.md)

Four required changes, G1 to G4, all taken. The four smaller points, H1 to H4, are not taken in this
revision: the lead limited revision 6 to decisions (f), (g) and (h) and the group key.

| Point | Checked against the code | Where it is fixed |
| :- | :- | :- |
| G1 decision (f) half carried | True, and revision 5's reason was wrong. Read in control_channel_presentation.py: a pick is accept and one or more value words (:176-181), every pick has the ruling approve (:255-265), and the presenter checks a request's choices only for a ruling each and for being distinct (:866-879). So member picks need no channel change. The size limit is real (:377-379). Of the two ways offered for a request that does not fit, neither is taken as written: the request keeps the group picks and offers the member picks that fit, which adds no console route and keeps one open group per day. "Keep, then Abandon" is deleted | 4.9, 6.6, section 7 item 4, section 10, section 13; ticket 0342 AC1 and AC2, ticket 0340 AC3, ticket 0327 AC1; the spec's AC3 |
| G2 decision (g) not carried | True: 6.5 and section 7 said Discard loses a detached worktree's commits. Taken as written. It has a ticket of its own, because 0318 is at four ACs | 4.9, 6.5, section 7 ("Which touchpoint", the Discard row, item 6), section 13; ticket 0343, ticket 0318 AC3, ticket 0327 AC2; the spec's AC3 |
| G3 decision (h) not in the table | True: the two volumes were named in a paragraph and were not rows. They were not listed again on the engines for this revision; the names are those of revision 5's listing | Section 11 (the table and the paragraph under it), section 13 |
| G4 no second group on one day | True: one record per scope and day could not be reopened and could not be written twice. The key is now scope, day and sequence number, and a deferral joins the open group or opens a new one. The day stays a key and no clock is added | 4.9, section 7 items 2 and 6, section 13; ticket 0342 AC3, ticket 0340 AC3; the spec's AC3 |

## 15. Open questions for the lead

Every question of revision 6 is decided and carried (section 13), (f), (g) and (h) included.

One point for the owner, from 7.1. The decision said one capability, cap_sys_ptrace, and listed fd
among what the reader reads. Measured: that one capability does not list the fd folder. This design
keeps the one capability and reads each descriptor's inode number from fdinfo, which costs a listing
of the item's files at every attempt. The other way is a second capability, cap_dac_read_search: the
reader could then print paths and the probe would compare paths as it does today, but that capability
lets its holder read every file on the host, and a mistake in the reader would be worth that much. The
design takes the first way. VELDO-0344 is written for it and changes only if the owner says so.
