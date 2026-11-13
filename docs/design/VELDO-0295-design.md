# VELDO-0295 design: space management

Design for the spec at
specs/VELDO-0295-veldo-records-what-it-creates-and-removes-it-at-the-event-that-ends-it.md. It answers
the owner's request (Telegram 41152): "for veldo we need to introduce space management - with all of the
projects, worktrees and tmp growing, veldo needs to clean things up after itself. this should happen not
just like once in a while, but we need to keep track of things that are created, changed, merged, etc and
have it part of the process".

The design in one paragraph: Veldo keeps a ledger in its control store. Every thing a Veldo process makes
on disk or in Docker is written to the ledger before it is made, with its owner and the events that end
it. When one of those events happens, the process that emits it asks the ledger which things are now due
and removes them on the spot, each through a fixed set of safety rules. A thing a rule refuses stays, is
marked deferred with the rule's name, and is tried again at its next event. A run states the space it
needs and waits when the pool cannot cover it. At service start, and when asked, Veldo compares the disk
and Docker with the ledger. There is no timer anywhere in it.

Four things the lead must know before reading on:

1. Things an agent's own commands create inside a run (a build folder, a container its tests start)
   cannot be recorded before they exist, because Veldo does not run those commands. They are recorded at
   the run's next event by a census of the run's worktree, its scratch root and its Docker label
   (sections 6.3 and 6.4). Nothing is removed before it is recorded.
2. A Docker object is owned by a run only when it carries the run's label or its compose project name. An
   object without either is reported and never removed. Section 6.4 says why nothing stronger is honest.
3. Removal inside a container engine that keeps its data in a disk image frees space inside the image
   and none on the host. The ledger records the two figures apart, and admission for such an engine is
   judged inside it (section 4.2).
4. The first reconcile on an existing host removes nothing. It lists what is due, and the owner confirms
   per project and kind (section 10).

## 1. What was measured

Measured read only on the owner's host on 2026-11-13. This section is provenance; the generic documents
carry none of these names.

| What | Measured |
| :- | :- |
| Filesystem | One filesystem of 915 GB holding the home folder and the temporary folder; 877 GB used, 29 GB free, 97 percent |
| core worktrees | 102 in git's list, 157 GB under the worktree root |
| Build folders in them | 8 folders, 89 GB together; the largest 35 GB, then 21 GB and 9 GB; two are named target-veldo1810, not target |
| veldo worktrees | 78 in git's list, 12 GB, after today's manual cleanup |
| seo worktrees | 8 in git's list, 5.4 GB, after today's manual cleanup |
| Session scratch under the temporary folder | 11 GB |
| System Docker engine (context default) | 13 containers, 51 volumes, 80 images (44 GB), 12 GB build cache; its data root is on the host filesystem |
| Desktop Docker engine (context desktop-linux) | 52 containers, 325 volumes (175 GB), 115 images (60 GB), 14 GB build cache; its data is one disk image, 276 GB allocated on the host |
| Containers with a compose project label, desktop engine | 49 of 52 |

What exists today, and the case each one misses:

| Mechanism | What it does | What it misses |
| :- | :- | :- |
| nightly_build_cleanup.sh, user schedule 03:17 | Removes build folders, session scratch and build caches unchanged for 2 days and at least 100 MB, after an in-use check | Acts by age. A folder made and finished today stays two days. It knows no owner, so it cannot tell a landed ticket from a live one. It never touches worktrees or Docker. It found named build folders only after nine of them held 49 GB |
| The gate script | Refuses under 60 GB free, deletes its build folder after the verdict | One script on one project. A gate that fails on a full disk still printed a red verdict until someone read the log |
| Builder briefs | Tell the builder to remove its own output | An instruction, not a mechanism. A run killed by a full disk removes nothing |
| Manual cleanup | Took the veldo and seo roots from 116 and 44 worktrees to 78 and 8 today | Needs a person, and the person has to work out by hand what is safe |

The standing owner decisions this design obeys: nothing that is in use is removed (33341); the places data
is never touched on either engine (32807); a Docker cleanup is never called safe without listing what it
removes, and the figure a Docker tool calls reclaimable is never quoted as a gain (35405); images that
cannot be pulled again are kept (2026-11-13); the desktop engine's disk image is not acted on.

## 2. Terms

| Term | Meaning |
| :- | :- |
| Item | One thing on disk or in Docker that the ledger has a record for |
| Kind | What an item is: worktree, branch, build output, scratch, evidence, container, volume, network, image tag |
| Owner | Who an item belongs to: always a project; where they apply, a ticket, a run, a gate and a lane |
| Pool | One body of storage whose free space is one number: a filesystem, or a container engine that keeps its data in its own disk image |
| Ending event | An event in the item's lifecycle at which the table in section 5 says to act |
| Due | An ending event has happened and the action has not been carried out yet |
| Deferred | Due, tried, refused by a safety rule; waits for its next event |
| Hold | The space an admitted run has been promised and has not yet used or given back |
| Floor | The free space a pool must keep after every admitted run has taken what it declared |
| Census | Reading what a run left behind (its worktree's untracked folders, its scratch root, its labelled Docker objects) and recording it |
| Protect list | Paths and Docker names that are never recorded, adopted or removed |

## 3. Components

Every file under engine/.veldo has a synced copy under .veldo that changes with it.

| Component | File | New or changed | Responsibility |
| :- | :- | :- | :- |
| Ledger | engine/.veldo/control_space.py | New | Owns the item, pool, hold and reconcile records in the control store. The only writer of them. Registers its commands and declares ownership of its entity kinds the way the reservation service does |
| Declarations reader | engine/.veldo/control_space_config.py | New | Reads the installation's space section and each project's space file, applies defaults, refuses a malformed one by name |
| Kind registry | engine/.veldo/control_space_kinds.py | New | Plain data and one pure function. For each kind: how an item is identified, its lifecycle table, which safety rules apply, which remover carries out each action |
| Probes | engine/.veldo/control_space_probe.py | New | The observers the safety rules read: process working directories and open files, container mounts, git state of a worktree and a branch, the protect list. Each returns facts; none decides |
| Removers | engine/.veldo/control_space_remove.py | New | One remover per action. Each uses the owning tool's own non-forced remove and reports what it measured |
| Signal | engine/.veldo/control_space_signal.py | New | The one entry point an emitting process calls with an event. Finds due items, runs rules and removers in line, writes the outcomes |
| Docker adapter | engine/.veldo/control_space_docker.py | New | Per engine context: the run label and compose project name, the snapshot, the event subscription, the census, the object removers |
| Reconciler | engine/.veldo/control_space_reconcile.py | New | Snapshot of roots and engines, comparison with the ledger, adoption rules, the report |
| Admission | engine/.veldo/control_space_admission.py | New | Pools, needs, holds, the wait queue and its wake-up, the no-space classification |
| Clone provisioner | engine/.veldo/control_clone.py | Changed | Declares the clone root, work tree and scratch folder before making them; teardown goes through Signal |
| Fleet worktrees | engine/.veldo/fleet.py | Changed | Declares the worktree before git adds it |
| Sandbox worktrees | scripts/agent_sandbox.py, prepare | Changed | Declares the private repository, the worktree and the branch before making them |
| Receiver | engine/.veldo/control_launch.py | Changed | Declares run folders (artifacts, receipts, token records); sets the run's label and space environment; runs the census and sends run finished; classifies a no-space end |
| Retirement | engine/.veldo/control_retirement.py | Changed | A pending retirement's retry also retries the dispatch's deferred items |
| Dispatch acceptance | engine/.veldo/control_dispatch.py | Changed | Asks Admission before a dispatch is accepted for launch; a wait keeps the dispatch prepared |
| Landing | engine/.veldo/control_landing.py and control_landing_station.py | Changed | After the completion receipt is recorded, sends landed for the unit |
| Gate host | scripts/gate_host.py and scripts/gate_host.json | Changed | States the gate's space need, asks Admission after taking the lock, answers NOT STARTED when it must wait; sends verdict recorded after the stamp is written |
| Authority service | engine/.veldo/control_service.py | Changed | At start: snapshot, subscribe, reconcile. Sends ticket closed and ticket superseded when it commits those transitions. Wakes waiting dispatches after a removal |
| API | engine/.veldo/control_api.py and engine/ui/src/api/routes.json | Changed | The space reads and the four owner actions of section 6.6 |
| Console | engine/ui/src/features/space, engine/ui/src/views/SpaceView.vue, engine/ui/src/app/navigation.ts | New and changed | The Space screen, the run view's space panel, the wait reason on the runs list |
| CLI | engine/bin/veldo | Changed | The verb space with status, reconcile, record, event and admit, for scripts that run outside the service |
| Boundary check | scripts/check_space_boundary.py, called from scripts/verify.sh | New | Refuses a creation primitive in Veldo's own code outside the ledger's seam |
| Scaffold | engine/.veldo/init_scaffold.py | Changed | Lays .veldo/space.yaml in a new project |

### Component view

```
  PROCESSES THAT EMIT EVENTS                      THE SPACE LIBRARY (runs inside the emitter)

  Receiver (one per dispatch)   - run finished -+
  Gate host (one per gate)      - verdict  - - -+     +=============================+
  Landing station               - landed  - - - +- -> | Signal                      |
  Authority service             - closed, - - - +     |  1 ledger: which items due  |
                                  superseded,         |  2 kind registry: action    |
                                  abandoned           |  3 probes: facts            |
                                                      |  4 rules: remove or defer   |
  CREATORS                                            |  5 remover: owning tool     |
  Clones, Fleet, Sandbox,       - declare, - - - - -> |  6 ledger: outcome          |
  Receiver, Docker adapter        confirm             +==============+==============+
                                                                     |
  Dispatch acceptance, Gate host  - admit  - -> Admission - - - - -> |
                                                                     v
  Authority service at start     - - - - - -> Reconciler - - > +===========+     +================+
  Console action, CLI                                          |  Ledger   | - > | Control store  |
                                                               +===========+     | (journal)      |
  Console (reads only, through the API)  <- - - - - - - - - - - - - - - - - - -  +================+
```

The library is not a daemon. It has no loop and no clock. It runs when a process calls it with an event
or a creation, and returns.

## 4. Data model

All records are entities of the control store, written only by the Ledger's registered commands, each
write one journal record. No second database.

### 4.1 Item

Identity: space:item: followed by a new identifier. One record per thing.

| Field | Content |
| :- | :- |
| kind | One of the nine kinds |
| host | The host the thing is on |
| pool | The pool its bytes count against |
| locator | For a disk kind: the absolute path. For a branch: repository and ref name. For a Docker kind: engine context, object id and name |
| parent | The item this one lives inside, when there is one (a build folder's worktree, a branch's repository) |
| owner | project (always); ticket, run, gate, lane where they apply |
| creator | The component that declared it, or census, or reconcile |
| adopted | True when reconcile created the record for a thing that already existed |
| state | declared, present, due, deferred, removing, removed, gone, kept |
| ends_on | The events of section 5 that apply to this item, copied from the kind registry at declaration with the registry's version |
| size | Bytes at the last measurement and the event it was measured at |
| deferral | The rule that refused, the event it was refused at, the event that retries it, the number of attempts |
| removal | The event, the emitting process, the method, bytes just before, pool free before and after, and for an engine pool the host figure apart |
| report | For an item reconcile could not give an owner: what was found and why no rule adopted it |

States and the moves between them:

```
  declare           confirm            ending event            rules pass          remover done
 (nothing) -> declared -> present - - - - - - - - - -> due - - - - - -> removing - - - - - -> removed
                 |           |                          |  ^
                 |           | found missing            |  | next event
                 v           v by reconcile             v  |
               gone        gone                       deferred

  kept: a present item whose table action at its last event is keep (a branch, an evidence folder)
```

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

Identity: space:hold: followed by the dispatch identity or the gate run identity.

| Field | Content |
| :- | :- |
| needs | Per pool, the bytes the run declared |
| source | declared, measured, or default, per pool |
| state | waiting, admitted, released |
| reason | For waiting: pool, need, free, held by others, floor, as numbers |
| used | Per pool, the measured size of the run's own items at its last event |

### 4.4 Reconcile record

Identity: space:reconcile: followed by a new identifier. It holds what started it (service start, console,
CLI), the roots and engines read, and the counts: matched, adopted, reported, gone, completed. The findings
themselves are item records.

## 5. Kinds and lifecycle

One table, held in the kind registry as data. "Remove" always means: through the safety rules of section
7, by the remover of section 6.5. An empty cell means the event does nothing to that kind.

| Kind | Run finished | Verdict recorded | Landed or contained | Ticket closed or superseded | Worktree abandoned |
| :- | :- | :- | :- | :- | :- |
| Scratch | Remove | Remove | Remove | Remove | Remove |
| Build output | Remove, unless the same ticket has a queued run on the same worktree; then ownership passes to that run | Remove | Remove | Remove | Remove |
| Container | Stop, then remove | Stop, then remove | Remove | Remove | Remove |
| Network | Remove, after its containers | Remove | Remove | Remove | Remove |
| Volume | Remove, after its containers | Remove | Remove | Remove | Remove |
| Image tag | | | Remove the tag | Remove the tag | |
| Evidence | Measure | Drop caches inside it; keep the rest | Keep | Remove only the files whose digest the store or the landed commit already holds; keep the rest | Keep |
| Worktree | Measure | | Remove with git's non-forced worktree remove, after its build output | Remove the same way; a worktree with unique work is deferred | Remove the same way; a worktree with unique work is deferred |
| Branch | | | Mark contained; keep | Keep | Keep |

The events, and who emits each:

| Event | It has happened when | Emitted by |
| :- | :- | :- |
| Run finished | The dispatch record is conclusive and the kernel says its containment group is empty (the VELDO-0041 conditions) | The receiver of that dispatch |
| Verdict recorded | A gate's stamp, or a review's verdict, is written | The gate host, or the review's receiver |
| Landed | The VELDO-0057 completion receipt for the unit is recorded | The landing station |
| Contained | A branch's tip is reachable from the trunk, from the source commit of a completed landing, or from another live branch | The landing station at each landing, for every recorded branch of the project; and reconcile |
| Ticket closed, ticket superseded | The authority commits that transition of the unit | The authority service |
| Worktree abandoned | The ticket's next run is provisioned in another worktree, or the owner presses Abandon on the console | The provisioner, or the API action |

Two rules complete the table. A worktree is never removed while an item inside it is present, due or
deferred, so the build output goes first and a deferred build folder holds its worktree. An item that has
no ticket (a gate on a batch, an adopted folder) ends on its run's or its gate's events only.

"Worktree abandoned" is an event, not an age. A worktree nobody has touched for a month is not abandoned
until one of the two things in the table happens.

## 6. Interfaces

### 6.1 Ledger commands

Each is a registered command of the control store, journaled and signed like every other.

| Command | Input | Effect | Refuses |
| :- | :- | :- | :- |
| declare | kind, host, locator, owner, creator, parent | Creates an item in state declared, with pool and ends_on filled in | A locator on the protect list; a locator outside every known root; a second live item with the same locator |
| confirm | item | declared to present | An item not in state declared |
| measure | item, bytes, event | Writes size | |
| signal | event, subject | Marks every present, kept or deferred item whose owner matches the subject and whose table has an action at this event as due; returns them in removal order | An unknown event |
| outcome | item, one of removed, deferred, kept, with the facts | Writes the state and the removal or deferral fields | An item not due or removing |
| adopt | what reconcile found, the rule that proved the owner | Creates an item in state present with adopted true | The same refusals as declare |
| report | what reconcile found | Creates or refreshes a report record; never an owner | |
| gone | item | present or declared to gone | |
| hold, admit, release | See 6.7 | | |

A creator that cannot reach the authority refuses its own creation as unavailable_service:space_ledger. A
repository with no central installation has no ledger; there every seam stands down and creates as today.

### 6.2 The seam a creator calls

Two calls around the creation: declare before, confirm after. If the creation fails, the creator calls
gone. The seam returns the item's identity, which the creator stores beside whatever record it already
keeps (the clone manifest, the dispatch record), so a teardown can name the item.

The boundary check keeps the set of creators complete. It reads Veldo's own code for the creation
primitives (git's worktree add, a new temporary folder, a container, volume, network or image creation
through the Docker client) and refuses any that is not inside a function the seam's list names. A new
creator is a change to that list, which a reviewer sees.

### 6.3 What a run is given, and the census

The receiver gives every run four things in its environment, each a path or a name the ledger already
holds:

| Given | What it is | Why |
| :- | :- | :- |
| A scratch root | The run's temporary folder, already declared as scratch | Everything a tool puts in the temporary folder lands in a recorded place |
| A build root | A folder for build output outside the worktree, already declared as build output, for projects that ask for one | Tools the project names are pointed at it through the variables the project declares |
| A space label | One string unique to the run | Section 6.4 |
| A compose project name | Derived from the label | Section 6.4 |

The census runs at each of the run's events (the end of each dispatch, and run finished), before Signal:

1. In the run's worktree, ask git for untracked paths, ignored ones included. Every ignored folder at any
   depth that git reports as a whole is a build output item, whatever its name. Ignored files that are
   not inside such a folder are left alone and not recorded. Untracked paths that git does not ignore are
   unique work: they are not recorded as items, and they protect the worktree (section 7).
2. Measure the scratch root, the build root, each build output found, and the worktree without them.
3. Ask the Docker adapter for the objects carrying the run's label or compose project name.
4. Declare what is new, confirm it, and write the sizes.

Why an ignored folder in a run's worktree may be treated as build output: a worktree Veldo made started
as a clean checkout, so every untracked thing in it was made by the run, and the project's own ignore
rules say which of those are not source. A project that keeps something precious in an ignored folder
names it in its keep list (6.8), and the census then leaves it out. This reasoning does not hold for an
adopted worktree, which Veldo did not make: there, only folders matching the project's declared build
output patterns are recorded, and nothing else.

### 6.4 Docker

A run's Docker objects are owned through two mechanisms that the tools themselves provide:

| Mechanism | Covers | How |
| :- | :- | :- |
| The compose project name in the run's environment | Everything a compose file creates: containers, networks, named volumes | Compose stamps its project name on each as a label. Verified on the measured host: 49 of 52 containers on the desktop engine carry it |
| The run's label | Objects Veldo itself creates (the container provisioner), and objects a project's own scripts create when the project passes the label on | Applied at creation |

An object created during a run with neither is not attributable. Two runs can share an engine, and the
engine's event for a new container does not say which process asked for it. So the adapter records such an
object as a report, shows it on the console with the runs that were live on that engine when it appeared,
and never removes it. The owner can assign it to a ticket with the Adopt action, after which the table
applies.

Per engine context the installation names, the adapter:

1. takes a snapshot at service start: containers, volumes, networks and images with their labels;
2. subscribes to the engine's event stream for as long as the service runs, and turns each create, start,
   stop and destroy event into a ledger write or a report;
3. on a broken stream, takes a new snapshot and reconciles before it subscribes again.

Images. An image tag a run built is an item and is removed with its ticket. An image a run pulled is not
an item: it is recorded once per engine as kept, with no ending event, because nothing in Veldo can prove
it can be pulled again. The protect list names the images known not to be.

### 6.5 Removers

| Action | Method | It refuses by itself when |
| :- | :- | :- |
| Remove a disk folder | Rename it to a marked name beside itself, run the in-use probe again on the new name, then delete it; if the second probe finds a user, rename it back and defer | The folder is a mount point, or is not on the item's pool |
| Remove a worktree | git's worktree remove, without the force option | git finds a modified tracked file or an untracked file |
| Remove an image tag | The engine's image remove, without the force option, on the tag | A container uses the image |
| Stop and remove a container | The engine's stop, then remove, without the force option | |
| Remove a volume | The engine's volume remove | A container uses the volume |
| Remove a network | The engine's network remove | An endpoint is attached |
| Drop caches in an evidence folder | Remove the sub-folders the project declares as caches; nothing else | |
| Mark a branch contained | A ledger write; git is not called | |

No remover calls a prune command, and none passes a force option. Each returns the bytes it measured just
before, and the pool's free space before and after.

### 6.6 API and console actions

Reads, all from ledger records, live through the existing record stream:

| Route name | Returns |
| :- | :- |
| space.pools | Each pool: capacity, free, floor, held, and the waiting holds with their numbers |
| space.usage | Bytes and item counts grouped by project, by ticket and by kind; filters for each |
| space.pending | Due and deferred items: owner, kind, locator, size, reason, the event that retries it |
| space.removed | Removed items, newest first: owner, kind, locator, event, emitter, size, free before and after |
| space.reports | What reconcile found and could not adopt, and unattributed Docker objects |
| space.protected | The protect list in force and where each entry comes from |

Owner actions, each a signed command through the API like every other owner action:

| Route name | Does |
| :- | :- |
| space.reconcile | Runs a reconcile now, for one project or all |
| space.adopt | Gives a reported thing an owner |
| space.abandon | Emits worktree abandoned for one worktree |
| space.confirm | Confirms a migration batch (section 10) |

### 6.7 Admission

| Call | When | Result |
| :- | :- | :- |
| hold | Dispatch acceptance, and the gate host after it has the lock | Writes a hold in state waiting with the needs |
| admit | Straight after hold, and again on every wake-up | Admitted, or waiting with the reason |
| release | Run finished, after Signal | Hold released |

Where a need comes from, first that applies: the dispatch contract or the gate's host configuration states
it; else the largest measured size of the last five finished runs of the same project and station; else
the pool's default need from the installation.

The rule, per pool: free now, minus what admitted runs still hold, must be at least the need plus the
floor. What a run still holds is its need minus the size of its own items at its last measurement, never
below zero. Free now is read from the filesystem or the engine at the moment of the call.

Before it answers waiting, admit runs Signal with the event admission requested for the pool, which
retries that pool's deferred items. If that frees enough, the run is admitted.

A waiting dispatch stays prepared. It is looked at again when a remover reports freed bytes on its pool,
when a hold on its pool is released, and after a reconcile. Those are the only wake-ups. Space the owner
frees by hand is seen at the next of them, or at once with Reconcile on the console.

A waiting gate answers NOT STARTED with the reason and exit 75, as it does today for a held lock.

### 6.8 Declarations

The installation's space section (the installation folder, read by the one installation reader):

| Key | Content |
| :- | :- |
| enabled | Off stops every removal and every admission check; the ledger stays readable |
| pools | Per pool: floor, default need |
| engines | The Docker contexts Veldo may read and act on |
| scratch roots | Folders outside projects where run and session scratch lives |
| protect | Path prefixes, and per engine: volume, container, image and compose project name patterns |
| mode | report, or act (section 10) |

A project's .veldo/space.yaml, laid by init:

| Key | Content | Default |
| :- | :- | :- |
| worktree root | Where the project's worktrees live | The folder beside the repository named after it with the suffix -worktrees |
| branch pattern | How a branch name gives a ticket | The agent branch patterns Veldo itself creates |
| build output | Extra folder name patterns, for adopted worktrees and for folders git does not ignore | None |
| build variables | Environment variables to point at the run's build root | None |
| keep | Ignored paths the census must leave alone | None |
| evidence caches | Sub-folders of an evidence folder that are caches | None |
| needs | Per station (build, review, gate): bytes per pool | Measured, then the pool default |
| protect | Additions to the installation's protect list | None |

A project may add protection. It cannot remove an installation entry.

## 7. Safety rules

Every removal passes these, in this order, and the first that refuses names the deferral. The rules read
the probes' facts at the moment of the attempt; no fact is carried over from an earlier attempt.

| Order | Rule | Refuses when | Deferral |
| :- | :- | :- | :- |
| 1 | Ledger | The thing at the locator is not the item recorded (another object id, another repository, a path that now resolves elsewhere through a link) | not_in_ledger |
| 2 | Protect | The locator, or anything beneath it, matches the protect list | protected |
| 3 | Owner live | The item's owning run is not conclusive, or its containment group is not empty | in_use |
| 4 | Process use | Any process has its working directory or an open file at or beneath the path; or a running container on any named engine mounts it; or git holds a lock on the worktree | in_use |
| 5 | Unique work | Worktrees only: a tracked file is modified or staged; or an untracked file exists that git does not ignore; or an operation is in progress (merge, rebase, cherry-pick); or the checked-out commit is reachable from no branch, no completed landing's source commit and not the trunk | unique_work |
| 6 | Children | An item inside this one is present, due or deferred | in_use |
| 7 | Tool | The owning tool's non-forced remove refuses | remove_refused |

Notes on the probes:

- Process use reads each process's working directory and open file links from the kernel's process
  table. A command line that mentions the path is not use: that test also matches the shell doing the
  check. The file-sharing helper of a desktop container engine holds descriptors on every path a
  container ever mounted and is not counted; the running containers' mount lists are read instead.
- The folder remover's rename closes the gap between probe and delete. A process that opens the folder
  after the first probe either fails to find it, or holds a file that the second probe sees under the new
  name.
- Unique work for a squash landing: the branch tip is not an ancestor of the trunk, but it is the source
  commit the completion receipt names, or an ancestor of it. That is why rule 5 reads the receipts.

Retry. A deferred item is made due again by its next ending event, by admission requested on its pool, by
the retry of its dispatch's pending retirement, and by reconcile. Nothing retries it on a clock. An item
deferred for unique work in a closed ticket has no further event of its own: it stays on the console until
the owner commits or discards the work and presses Reconcile, or presses Abandon.

The protect list is also read at declare and at adopt, so a protected thing never gets an item record. It
appears under space.protected, and that is all.

## 8. Data flows

### 8.1 A build run, start to end

1. Dispatch acceptance writes the hold and asks admit. Waiting: the dispatch stays prepared and the
   console shows the numbers. Admitted: go on.
2. The provisioner declares the worktree (or clone work tree), its branch and its scratch folder, makes
   them, and confirms each.
3. The receiver declares the run folders and the build root, sets the four environment values and starts
   the worker in its containment group.
4. The worker runs. Veldo does nothing during the run.
5. The worker and its group end. The receiver records the dispatch's end as it does today.
6. The receiver runs the census: new build output, Docker objects with the run's label, sizes.
7. The receiver calls Signal with run finished. Scratch, containers, networks and volumes are removed.
   Build output is removed, or passes to the ticket's queued run on the same worktree.
8. The receiver releases the hold. Waiting dispatches on the pool are looked at again.
9. The receiver exits.

### 8.2 A gate

1. The gate host takes the host lock, writes the hold and asks admit. Waiting: NOT STARTED, exit 75.
2. The gate runs in its scope. Its trial worktree and build folder were declared by whoever made them.
3. The stamp is written. That is the verdict; nothing before this step removes anything.
4. The gate host runs the census and calls Signal with verdict recorded. The build folder goes; the
   evidence folder's caches go; the evidence stays.
5. The gate host releases the hold and exits.

### 8.3 A landing

1. The landing station records the completion receipt.
2. It calls Signal with landed for the unit. The unit's worktrees lose what build output they still have
   and are then removed by git; the branch is marked contained and kept; image tags go.
3. It computes contained for the project's other recorded branches against the new trunk tip and calls
   Signal for each that became contained.

### 8.4 A deferral and its retry

1. Signal finds a build folder due. Rule 4 finds a process with an open file in it.
2. The outcome is deferred, in_use, with the event that refused it. The console lists it.
3. Later the ticket's next run finishes. Signal makes the folder due again, the rules pass, it is
   removed, and the removal names this second event.

### 8.5 Reconcile

1. Snapshot. For each bound repository, git's own list of worktrees and branches. For each project's
   worktree root, each scratch root and the state root, the entries one level down. For each worktree
   found, the census of section 6.3. For each engine, the adapter's snapshot.
2. Subscribe. The Docker adapter's event streams. On disk there is nothing to subscribe to: the creators
   report through the seam, and the census reads the rest at events.
3. Compare, and for each difference do one thing:

| Found | Ledger | Result |
| :- | :- | :- |
| Thing | Matching item | Matched; size refreshed |
| Nothing | Item present or declared | gone |
| Half-removed folder under its marked name | Item removing | Removal completed |
| Worktree in a bound repository's list, under the project's worktree root, on a branch the branch pattern maps to a ticket | None | Adopted, owner that ticket |
| Worktree as above, branch maps to no ticket | None | Adopted, owner the project only; it ends on Abandon alone |
| Folder matching the project's build output patterns inside an adopted or recorded worktree | None | Adopted, parent that worktree |
| Clone folder with a valid manifest under the state root | None | Adopted, owner the manifest's dispatch |
| Docker object with a Veldo run label or a run's compose project name | None | Adopted, owner that run |
| Anything on the protect list | None | Listed as protected; no item |
| Anything else under a root or on an engine | None | Reported |

4. For each adopted item, read its owner's current state and mark the item due if an ending event for it
   is already in the past (its ticket landed last week). In mode act these go through Signal at once. In
   mode report they wait for the owner's confirmation.

Reconcile is the only place where an action follows from a state instead of from an event as it happens.
It runs at service start and when asked, and never on a schedule.

### 8.6 A run that hits a full pool

1. The run or gate ends without success.
2. The receiver or gate host reads the pool's free space, before the census and before any removal, and
   searches the run's output for the operating system's no-space error.
3. Both true (the error is there, and free space is under the floor): the end is recorded as
   environment_failure:no_space. No verdict is written, the gate answers NOT JUDGED with exit 75, and the
   unit is not charged a failed attempt.
4. The error is there and free space is not under the floor: the end is unknown_outcome:no_space_unconfirmed.
   No verdict is written and the run is repeated once. A second end of the same kind stands as what it is.
5. Either way the census and Signal run as for any finished run, with one exception: rule 5 keeps the
   worktree, because a run killed mid-work leaves uncommitted changes, and the next brief for the ticket
   says the worktree holds them.
6. The unit goes back behind admission. Two environment failures in a row for one unit raise an andon to
   the owner and stop the repeats.

## 9. Deployment view

```
  ONE HOST
  +=======================================================================================+
  |                                                                                       |
  |  Authority service (one process)          Factory state root                          |
  |    control store  <- - - - - - - - - - -   control.sqlite3 (ledger records live here) |
  |    Reconciler at start                      clones/  caches/  artifacts/  receipts/   |
  |    Docker adapter: one event                                                          |
  |      stream per engine context            Installation folder                         |
  |    wake-ups for waiting dispatches          installation.yaml (space section)         |
  |                                                                                       |
  |  API process  -> console in the browser   Project A repository        Project B ...   |
  |                                             .veldo/space.yaml                         |
  |  Receiver (one per dispatch)                worktree root                             |
  |    space library, in line                     worktree, build output                  |
  |                                                                                       |
  |  Gate host (one per gate)                 Scratch roots                               |
  |    space library, in line                   run scratch, session scratch              |
  |                                                                                       |
  |  Landing station                          Container engine 1: data root on the        |
  |    space library, in line                   filesystem (same pool as the filesystem)  |
  |                                           Container engine 2: data in a disk image    |
  |                                             (a pool of its own)                       |
  +=======================================================================================+
```

Who may write what:

| Process | Writes the ledger | Removes things |
| :- | :- | :- |
| Authority service | Directly; it is the store's writer | Reconcile's completions, ticket closed and superseded |
| Receiver, gate host, landing station | Through the authority, as signed commands | Yes, in line, at their own events |
| Worker (the agent) | Never. It has no store connection | Whatever its own commands do inside its worktree, as today |
| API | Owner actions, through the authority | No. Abandon and Confirm make the authority act |
| CLI | Through the authority | Only what Signal does for the event it was given |

Several hosts. An item names its host. Signal acts only on items of the host it runs on; an item on
another host becomes due and is carried out by that host's receiver or service at its next event or
reconcile. This design builds and proves one host. The second host is covered by the same records and is
not exercised until a ticket asks for it.

Order of start: the authority service opens the store, attaches the Ledger, then runs reconcile (snapshot,
subscribe, compare) before it accepts a dispatch. A reconcile that fails is reported by name and the
service serves everything else; admission then uses the last known holds and the live free space.

## 10. Console

One new screen, Space, in the factory group of the navigation.

| Section | Shows |
| :- | :- |
| Pools | One row per pool: capacity, free, floor, held; under it the waiting runs with need, free, held and floor |
| Usage | A table that groups by project, then ticket, then kind, with bytes and counts; each size names the event it was measured at |
| Pending removal | Due and deferred items with the reason in words (in use by process 4412; uncommitted changes in 3 files; protected by the installation) and the event that will retry |
| Removed | The removal history: what, whose, which event, how much, free space before and after; for an engine pool the note that the host figure did not change |
| Reports | Things found with no owner, each with Adopt; Docker objects no run could be named for |
| Protected | The list in force |

Elsewhere: the run view gains a space panel (the run's items, their sizes, what was removed at its end);
the runs list shows a waiting run's reason in one line; the overview shows a pool under its floor.

In report mode the Pending removal section groups due items by project and kind with one Confirm per
group.

## 11. Migration

1. Install with mode report. The service starts, reconciles, adopts and reports. Nothing is removed.
2. The owner reads Reports and Protected, and adds what is missing to the protect list. On the measured
   host that is: the places volumes, containers, images and backup folder on both engines; the project
   database volumes; the object-store images that can no longer be pulled; the integration checkout and
   the gate's own checkout, whose caches a full check reuses.
3. The owner confirms pending groups, one project and kind at a time. Each confirmation runs Signal for
   that group through all seven rules.
4. Set mode act. From here removals happen at events.
5. Retire the nightly script, by the check below.

The nightly script's cases and what covers each:

| The script removes | Covered by |
| :- | :- |
| Folders named target in the project's worktrees, to four levels | Build output by census (any ignored folder) and by declared patterns in adopted worktrees; removed at run finished, verdict recorded or landed |
| Folders named target- and a suffix | The same; the name does not matter |
| Folders with target in the name under the session scratch root | The run's build root and scratch root, declared at run start; older ones adopted as scratch |
| Per-session scratch folders | Scratch items; a lead session that is not a Veldo run records its scratch through the CLI at start and sends its own finished event at end |
| Folders with target in the name under the user's cache folder | Named as a scratch root in the installation; adopted, then owned like any other |
| Its keep list (two checkouts) | Protect entries |

The retirement check: run the script in its dry-run mode on the live host on three days; on each, every
path it lists must already be an item in the ledger. When that holds, remove its schedule entry and keep
the file. If the check lists a path the ledger does not hold, that path's class is a gap and the script
stays.

One case the events do not cover by themselves: scratch made by a session that never tells Veldo it
ended (a crashed terminal). Its owner is a session, and rule 3 reads the session's process from the
kernel; once that process is gone the item is removable, and it becomes due at the next reconcile.

## 12. Tickets

Each ticket is one concern and becomes its own spec. The numbers are reserved by this design. "Row" is a
row of a suite; each falsifier is the one change that must turn its row red.

Build order: 0296, 0297, 0298 and 0299 together, 0300, 0301, then 0302 to 0305 in any order, 0306, 0307,
0308, 0309, 0310.

### VELDO-0296 The ledger: item, pool, hold and reconcile records in the control store

Depends on nothing new. Components: Ledger.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The commands of 6.1 write items through the states of 4.1 and no other move is accepted: confirm only from declared, outcome only from due or removing | Accept outcome removed on a present item; the row that sends it without a signal sees the item removed and fails |
| AC2 | Only the Ledger's module writes these entity kinds; the store's generic entity command is refused for them | Leave the kinds undeclared; the row that writes an item through the generic command succeeds and fails |
| AC3 | declare refuses a second live item at the same locator, and a locator outside every known root | Compare locators as raw text; a second declare through a path with a trailing separator is accepted and the row fails |
| AC4 | A store rebuilt from its journal holds the same items, pools and holds | Keep sizes in a side table outside the journal; the rebuilt store's item has no size and the row fails |

### VELDO-0297 Declarations: the installation's space section and the project's space file

Components: Declarations reader, Scaffold.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The installation section and the project file are read with the defaults of 6.8; a malformed key is refused by its name | Ignore an unknown key; the row with a misspelled floor key gets the default floor and fails |
| AC2 | A project with no file gets every default and is not refused | Require the file; the fixture project without one is refused and the row fails |
| AC3 | A project's protect entries add to the installation's and cannot remove one | Let the project list replace the installation list; the installation's protected volume pattern is gone from the result and the row fails |
| AC4 | init lays the file, and the generic documents that describe it pass the docs check | Write a project name into the template; the docs check row fails |

### VELDO-0298 The kind registry and the lifecycle table

Components: Kind registry. Pure data and one function; no file, process or store access.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | For every kind and every event the function returns exactly the action of the table in section 5; the rows are the whole table, cell by cell | Give worktree the action remove at run finished; that cell's row fails |
| AC2 | A worktree is never returned for removal while a child item is present, due or deferred, and due items come back children first | Return items in ledger order; the row with a deferred build folder gets its worktree first and fails |
| AC3 | Build output at run finished passes to a queued run of the same ticket on the same worktree instead of being removed | Remove whenever the owning run is finished; the row with a queued run loses the folder and fails |
| AC4 | An item keeps the table version it was declared under, and a registry change does not alter what an existing item ends on | Read ends_on from the current registry; after a fixture registry change the old item's events differ and the row fails |

### VELDO-0299 The safety rules and their probes

Components: Probes, and the rule order of section 7.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A path is in use when a live process has its working directory or an open file at or beneath it, or a running container mounts it; a command line naming it is not use | Check the working directory only; the row with an open file beneath the path reads not in use and fails |
| AC2 | A worktree has unique work in each of the five cases of rule 5, and has none when its commit is the source of a completed landing | Test ancestry of the trunk only; the squash-landed row reads unique work and fails |
| AC3 | A locator at or above a protect entry, or with one beneath it, is protected | Match the protect list on equal paths only; the row whose folder contains a protected folder reads unprotected and fails |
| AC4 | The rules run in the order of section 7 and the first refusal names the deferral | Run unique work before protect; the protected worktree with an edit is deferred as unique_work and the row fails |

### VELDO-0300 The removers

Components: Removers.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A folder is removed by rename, second probe, delete; a process that opens a file in it between the two probes gets the folder back under its own name | Delete after the first probe; the row that opens a file in the gap finds the folder gone and fails |
| AC2 | A worktree is removed only by git's non-forced remove, and a refusal by git is the deferral remove_refused with the worktree untouched | Pass the force option; the row with an untracked file loses it and fails |
| AC3 | No remover runs a prune command or a force option on any tool; the row reads every command each remover ran | Use the engine's volume prune for volumes; the command row fails |
| AC4 | Each remover returns the item's bytes just before and the pool's free space before and after, and for an engine image pool the host figure apart | Report the engine's own reclaimable figure as freed; the row that compares it with the measured free space fails |

The builder verifies with a test what git's non-forced worktree remove does with ignored files, and
records the result in the proof. The design does not depend on the answer, because build output is removed
before the worktree.

### VELDO-0301 Signal: an event removes what is due, in the emitter's process

Components: Signal. Depends on 0296, 0298, 0299, 0300.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A call with an event makes the matching items due, carries each out through rules and remover, and writes each outcome before it returns | Return after marking due and remove on a later call; the row that reads the disk as the call returns finds the folder and fails |
| AC2 | A refused item is deferred with the rule's name and is carried out by the next event for it | Drop a refused item back to present; the next event's row finds no deferral record and fails |
| AC3 | With the installation's switch off, or mode report, a call writes due and removes nothing | Ignore the mode; the report-mode row finds the folder gone and fails |
| AC4 | No clock is read to decide a removal: with the fixture clock moved 30 days and no event, nothing changes | Add an age rule for scratch; the clock row finds scratch removed and fails |

### VELDO-0302 Veldo's own creators declare before they create

Components: Clone provisioner, Fleet worktrees, Sandbox worktrees, Receiver's run folders, Boundary check.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each creator's thing has a declared item before it exists and a present item after, with project, ticket, run and lane as owner | Declare after creating; the row that kills the creator between the two finds a folder with no item and fails |
| AC2 | A creator that cannot reach the ledger creates nothing and refuses unavailable_service:space_ledger; with no central installation it creates as today | Create anyway on a refused declare; the row finds the folder and fails |
| AC3 | The boundary check refuses a creation primitive outside the seam's list | Add a worktree add in a new function not on the list; the check stays green and its mutation row fails |
| AC4 | A clone's teardown and a fleet worktree's removal go through Signal, and their existing refusal for a clone in use is unchanged | Call the old teardown directly; the item stays present after the folder is gone and the row fails |

### VELDO-0303 The run census and the run's space environment

Components: Receiver.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | At each run event every ignored folder git reports in the run's worktree becomes a build output item, whatever its name and depth; a keep entry is left out | Match the name target; the row's folder named otherwise has no item and fails |
| AC2 | An untracked path git does not ignore is never recorded as build output and makes the worktree unique work | Record every untracked folder; the row's new source folder becomes build output and fails |
| AC3 | The run's temporary folder and build variables point at folders declared before the worker starts | Set the variables without declaring; the row finds the build root with no item and fails |
| AC4 | In an adopted worktree only folders matching the project's declared patterns are recorded | Apply the ignored-folder rule to adopted worktrees; the adopted fixture's ignored data folder becomes build output and fails |

### VELDO-0304 Docker objects: label, snapshot, events, removal

Components: Docker adapter. Rows run against a stand-in engine; one integration row runs against a real
one with objects the row itself creates.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An object carrying the run's label or compose project name is an item owned by that run, on the context it was created on | Read one context only; the object on the second context has no item and fails |
| AC2 | An object created during a run with neither is a report, is never an item, and is never removed | Attribute it to the only live run; the row with two live runs gives it an owner and fails |
| AC3 | At run finished the run's containers are stopped and removed, then its networks and volumes, each by the engine's non-forced remove; a volume a container still uses is deferred | Remove volumes first; the engine refuses, the item is deferred, and the row that expects it gone fails |
| AC4 | A pulled image is recorded as kept with no ending event; a tag the run built is removed at landed or ticket closed; an image on the protect list is never an item | Treat pulled images as image tags; the row's pulled image is removed at ticket closed and fails |

### VELDO-0305 The lifecycle events are emitted where they happen

Components: Receiver, Gate host, Landing, Authority service, Retirement.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Run finished is sent by the receiver only after the dispatch is conclusive and its group is empty, and the removal is complete before the receiver exits | Send it when the worker's own process exits; the row with a surviving child process has its build folder judged while the child lives, and fails |
| AC2 | Verdict recorded is sent after the stamp is written, never before; a gate killed before its stamp sends nothing | Send it before the stamp; the row that kills the gate between the two finds the build folder gone with no verdict and fails |
| AC3 | Landed is sent after the completion receipt; the unit's worktree is removed, its branch kept and marked contained, and every other recorded branch the new tip contains is marked too | Skip the other branches; the row's second contained branch stays unmarked and fails |
| AC4 | Ticket closed, ticket superseded and worktree abandoned each reach Signal from the transition or action that makes them true, and a pending retirement's retry also retries that dispatch's deferred items | Leave superseded unwired; the superseded ticket's scratch stays present and the row fails |

### VELDO-0306 Reconcile at start and on demand

Components: Reconciler, Authority service.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Each row of the table in 8.5 gives its result | Adopt every folder under a root; the row with no provable owner gets an item and fails |
| AC2 | Reconcile completes a removing item and marks a missing one gone, and removes nothing else that was not already due | Remove reported things; the reported fixture folder is gone and the row fails |
| AC3 | The service reconciles before it accepts its first dispatch, and a failed reconcile is reported by name while everything else is served | Reconcile in the background; the row that sends a dispatch at once is admitted against an empty ledger and fails |
| AC4 | Nothing runs reconcile on a schedule: the only callers are service start, the API action and the CLI | Add a periodic call; the row that counts reconciles over a long idle fixture run finds more than one and fails |

### VELDO-0307 Admission by pool, need, hold and floor

Components: Admission, Dispatch acceptance, Gate host.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A run is admitted only when free space minus what others hold is at least its need plus the floor; the rows are the boundary values on both sides | Ignore the floor; the row between need and need plus floor is admitted and fails |
| AC2 | A waiting dispatch stays prepared with its numbers recorded, and is admitted without any other action when a removal or a release frees enough | Wake on a timer only; with the fixture clock stopped the row never admits and fails |
| AC3 | The need comes from the contract, else from the last five measured runs of the project and station, else from the pool default | Use the default always; the row with a measured history larger than the default is admitted too early and fails |
| AC4 | A gate that must wait answers NOT STARTED with the reason and exit 75, with no stamp and no event | Start the gate and warn; the row finds a stamp and fails |

### VELDO-0308 A run that ends on a full pool is an environment failure

Components: Receiver, Gate host.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | An unsuccessful end with the no-space error in its output and free space under the floor is environment_failure:no_space: no verdict, no failed attempt charged, the unit queued again behind admission | Record the gate's red; the row finds a red stamp and fails |
| AC2 | The error with free space above the floor is unknown_outcome:no_space_unconfirmed and is repeated once; a test that prints the error text and then fails for its own reason ends red on the repeat | Treat the text alone as an environment failure; the row's failing test never records its red and fails |
| AC3 | The worktree of a run that ended this way is kept with its uncommitted changes, and the next brief for the ticket says so | Remove the worktree at run finished; the row finds the edit lost and fails |
| AC4 | Two environment failures in a row for one unit raise an andon and stop the repeats | Repeat without a bound; the row counts a third attempt and fails |

### VELDO-0309 The console's Space screen

Components: API, Console.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The usage table's figures per project, ticket and kind equal the sums of the fixture's item records | Sum only present items and leave out deferred ones; the totals row fails |
| AC2 | Pending removal lists every due and deferred item with its reason in words and its retry event; Removed lists every removal with its event, size and free space before and after | Hide deferred items; the row that expects the in-use folder finds nothing and fails |
| AC3 | Reconcile, Adopt, Abandon and Confirm are signed owner commands; a session without the owner's passkey is refused each | Accept Abandon as a plain read route; the unsigned row succeeds and fails |
| AC4 | A waiting run shows need, free, held and floor on the runs list and the Pools section, and the screen updates from the record stream without a reload | Poll on an interval; the row that stops the fixture clock sees no update and fails |

### VELDO-0310 Migration, and retiring the nightly script

Components: Reconciler (mode), Console (Confirm), documents. Depends on every ticket above.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | In mode report a reconcile over a fixture with 20 worktrees, their build folders and labelled Docker objects adopts them and removes nothing | Act on due items in report mode; the row finds a folder gone and fails |
| AC2 | Confirm for one project and kind removes exactly that group's due items, through all seven rules | Confirm everything pending; the other project's folder is gone and the row fails |
| AC3 | The retirement check passes only when every path the nightly script's dry run lists is a ledger item, and it names the class of a path that is not | Compare counts instead of paths; the row with one uncovered path and one extra item passes and fails |
| AC4 | docs/runbook.md gains the situation "the disk is full or a run is waiting for space", docs/setup.md and docs/installation.md describe the declarations, and all three pass the docs check | Name the measured host's project in the runbook; the docs check row fails |

## 13. Decisions taken in this design

| Decision | Why |
| :- | :- |
| The ledger is records in the existing control store, not a new database | One writer, one journal, one place the console already reads. The volume is hundreds of records a day |
| The library runs inside the emitting process; there is no space daemon | The owner asked for cleanup as part of the process. A daemon would need to learn about events after the fact, which is polling |
| Admission double counts on purpose | Free space already reflects what running runs have written, and their unspent hold is subtracted as well. The error is on the safe side and shrinks at each measurement |
| Branches are kept | The owner's request names keeping the branch. A contained branch costs almost nothing, and deleting one is not undone by a rebuild |
| Pulled images are never removed | Nothing in Veldo can prove an image can be pulled again, and one that could not cost a whole run on 2026-11-13 |
| Unlabelled Docker objects are reported, not guessed | A wrong guess removes another run's database |
| Reconcile may act on a past event | Otherwise an adopted worktree whose ticket landed last month would never be removed. It is bounded to service start and an explicit request |

Left out, each a later ticket if wanted: a second host; build caches shared between worktrees; shrinking a
container engine's disk image; removing contained branches; a per-ticket space budget.

## 14. Open questions for the lead

1. Floors and default needs for the measured host. Today's practice is a 60 GB refusal for a gate and 40
   GB for a builder. Proposed: floor 40 GB on the filesystem pool, gate need 50 GB, builder need 16 GB.
   The disk has 29 GB free now, so with any of these every heavy run waits until the first confirmations
   free space.
2. Docker ownership for projects whose tests start containers without compose. They must pass the run's
   label on, which is a change in each such project. Until then their objects are reports. Is that
   acceptable for the first release?
3. Lead sessions that are not Veldo runs (the scratch under the session root). The design records them
   through the CLI at session start and end. Should Veldo instead refuse to count them and leave that
   folder to its owner?
4. Whether the ticket numbers are free: this design reserves VELDO-0296 to VELDO-0310. No
   branch held a number above VELDO-0294 on 2026-11-13.
5. A worktree deferred for unique work in a closed ticket stays until the owner acts. Should Veldo offer
   to save that work as a commit on a kept branch and then remove the worktree, or is that a decision only
   the owner makes each time?
