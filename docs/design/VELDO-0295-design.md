# VELDO-0295 design: space management

Revision 6, 2026-11-13. Design for the spec at
specs/VELDO-0295-veldo-records-what-it-creates-and-removes-it-at-the-event-that-ends-it.md. It answers
the owner's request (Telegram 41152): "for veldo we need to introduce space management - with all of the
projects, worktrees and tmp growing, veldo needs to clean things up after itself. this should happen not
just like once in a while, but we need to keep track of things that are created, changed, merged, etc and
have it part of the process".

The first rule of the design is section 0, from the owner's second message (Telegram 41209): no work
is ever lost. Space management saves work before it removes anything, and where it cannot save, it
does not remove. Every other section is read under that rule.

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

Amended a fourth time 2026-11-13, by the owner's rule (Telegram 41209), in the new section 0, and in
sections 2, 3, 4.1, 4.10, 6.1, 6.2, 6.3, 6.5, 6.6, 6.8, 6.11, 7, 8.8, 10, 11, 12, 13 and 15:

- No work is ever lost is the first rule. Section 0 says what work is, and that a removal saves it
  first or does not happen.
- Every commit a worktree or a private repository reaches is recorded on a kept ref,
  refs/veldo/kept/<ticket>/<item>, in its main repository before the removal. The removal is refused
  when that write fails.
- Discard saves the uncommitted state before it removes, so a Discard can be undone. Review scratch
  is saved the same way before it is deleted. (First as a commit on a kept ref; since the fifth
  amendment as files outside git.)
- An ignored file that is not build output is work. A git repository is treated as one in any folder:
  worker clones, batch clones and candidate workspaces are private repositories and no longer scratch.
- The owner gets removed work back with veldo space restore, or with plain git.
- Four more tickets, VELDO-0345 to VELDO-0348. The last is a suite that plants work and drives every
  removal path at it, and act mode is refused until it has passed on the host.

Amended a fifth time 2026-11-13, in 7.1, in sections 0, 2, 3, 4.1, 5, 6.1, 6.5, 6.6, 6.8, 7, 8.8, 9, 10, 12,
13, 14.6 and 15. Two things, both the lead's:

- Section 7.1 is in its second revision, after its validation (verdict CHANGES, three blocking points;
  14.6). The reader runs in a socket-started user unit of its own, because the service's
  NoNewPrivileges would leave it with no capability. It reads every thread of a process. Its binary is
  built from the reviewed commit and compared with a digest the gate recorded. Matching is by inode
  number alone. One capability stays.
- The lead answered the six questions section 15 put about section 0. The one that changes the design:
  a snapshot of uncommitted, untracked or ignored files is stored outside git, in a folder under the
  state root, so that a secret in an ignored file never enters a repository's object store. A dead
  run's worker clone with uncommitted files is saved and removed with no request. The other four stay
  as designed. Section 13 records all six, and section 15 is empty.

Amended a sixth time 2026-11-13, after the validation of section 0 and of 7.1's second revision
(design-veldo-nowork-0344r2-validation-2026-11-14.md, verdict CHANGES; 14.7), in sections 0, 2, 3, 4.1,
5, 6.1, 6.5, 6.6, 6.10, 7, 7.1, 8.8, 10, 12, 13, 14.7 and 15. The validation found three paths that
could still lose work, or report lost work as restored:

- A worker clone, a batch clone and a candidate workspace were still declared and adopted as scratch
  in four places. They are items of the kind agent repository everywhere, they take the keep step like
  any worktree, and a git repository found in an item of another kind holds that item (0.1, section 5,
  6.10, 8.8).
- The snapshot's failure, crash and retry paths are written out. Every attempt gets a folder of its
  own that is never replaced and never deleted. A save that fails or stops half way refuses the
  removal. A crash between the save and the removal is picked up from the ledger. Review scratch and a
  worker clone are compared file by file just before each file is deleted (0.2, 0.3).
- A restore that cannot find or verify its snapshot refuses and says so. Reconcile and veldo space
  kept check every kept ref and every snapshot against the keep records, and a missing one is
  reported until it is back (0.3, 0.5, 8.8).

Smaller: an agent worktree's kept refs go to the shared repository; a clean clone is read more
strictly; the suite plants five more shapes; the probe holds the reader's writer by a pidfd, and the
reader waits for the probe before it exits; the install line reads the source past git's replace refs
(0.2, 0.1, 0.7, 7.1).

Amended a seventh time 2026-11-13, after the final check of the sixth amendment
(design-veldo-nowork-r2-validation-2026-11-14.md, verdict CHANGES; 14.8), in sections 0, 3, 4.1, 6.1,
6.6, 7.1, 8.8, 12, 13, 14.8 and 15. The check found every earlier point resolved and two new defects,
one in each addition:

- The keep record named one snapshot, and a retry wrote the record again. When a removal that deletes
  file by file had stopped part way, the retry's snapshot took the first one's place in the record. A
  restore then brought back only the second and said success. The record now lists every attempt and
  no later write takes one off; restore applies them all, the oldest first (0.3, 0.5).
- A process could write a fake table to the probe and then execute the real reader in its own place,
  and the probe read the real reader's status for the fake bytes. The reader now writes its header
  only after it has locked itself, and the table only after the probe has seen it locked and sent one
  byte (7.1).

The lead also answered the one open question: the guard hook refuses a shell command that names the
snapshot store or the kept refs. That is one more ticket, VELDO-0349, built after 0346 (0.3, sections
12, 13 and 15).

Amended an eighth time 2026-11-13, for the two points of that check the seventh amendment left out,
F3 and F4 (14.8), in sections 0, 6.5, 7, 8.8, 12 and 14.8. The lead's word: both are required under
the owner's rule, F4 included.

- A removal that the comparison with the manifest stops inside a renamed folder renames the folder
  back to its locator before the item is deferred. Left under its marked name the item had nothing
  at its locator, and reconcile marked it gone with an unsaved file still in the folder (0.3, 6.5,
  8.8).
- Discard and Save move the worktree to a marked name with git's worktree move and look at it once
  more under that name before they remove it. The last look and git's one remove command no longer
  have a moment between them in which a file written by the worktree's path goes unsaved (0.3, 6.5,
  section 7).
- An attempt folder in the snapshot store that no keep record names is listed under its item and
  goes with that item's drop. None is left to grow unseen (0.3, 0.5).

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

## 0. No work is ever lost

The owner's rule (Telegram 41209): "It's very important no work is ever lost. Space management needs to
ensure this very clearly". It is the first rule of this design. Where another section disagrees with
this one, this one holds.

The rule, in one sentence: space management never removes the only copy of work. Before a removal it
saves the work where the owner can get it back with one command, and when it cannot save it, it does
not remove.

The reviews of the first tickets found five probes that answered "free" when they could not look, and
reproduced two losses: a kept worktree's uncommitted files, taken with the agent repository around it,
and a repository with its only commit, taken through an ignored folder. Each was closed where it was
found. This section states the rule those fixes serve, so that the next path is judged against the rule
before it is built and not found by a reviewer after.

Three terms. A private repository is a git repository made for one run: an agent repository, a worker
clone, a batch clone or a candidate workspace. Its main repository is the shared repository the
declarations name for it. The main repository of a worktree is the repository it is linked to, with
one exception: an agent's worktree is linked to its agent repository, which is itself removed later,
so its main repository is that agent repository's main repository, the shared one. A main repository
is therefore never a private repository. A kept ref is a ref under refs/veldo/kept/ in a main
repository; 0.2 says how one is written and why it stays. A fourth term comes with 0.3: the snapshot
store, a folder outside git where changes that are in no commit are saved.

### 0.1 What work is

| Work | Where it is found | What the rule does with it |
| :- | :- | :- |
| A commit no kept ref holds | The commit a worktree has checked out; a commit only a worktree's own log or own refs name; every commit in a private repository | It is recorded on a kept ref in the main repository before the removal (0.2) |
| Uncommitted changes | Tracked edits, staged changes, an operation in progress | Never removed before they are saved outside git, and in a worktree never without the owner's Discard (0.3) |
| Untracked files | Files git does not track. Ignored files are included unless they are build output | The same |
| Stashes | The stash entries of a shared repository, and those of a private repository | A shared repository's stash entries are never touched. A private repository's are unique work, and they go to kept refs before the repository goes |
| Unpushed branches | Branches and tags | No branch and no tag is ever deleted. Those of a private repository go to kept refs before it goes |
| Evidence and proof files | Evidence folders, gate logs and stamps, review reports, receipts, artifacts, proof bundles | Kept. A file is removed only when a copy with the same digest is held where this rule keeps it (0.4) |
| Anything the owner marked Keep | An item in state kept, a keep entry of a project, a protect entry | It is never due and never proposed, and it holds whatever it is inside (0.4) |

What is not work: build output, a run's scratch, a session's scratch, a run's own containers, networks
and volumes, and an image tag a run built. A build or a run makes each of them again. A thing is one of
these only by a declaration: an ignore rule the project has committed or a build output pattern it
declares, the scratch root Veldo gave the run, the run's label on a Docker object. Whatever cannot be
shown to be one of them is work.

Two things follow from that last sentence, and both change what earlier sections say.

An ignored file is build output only when a committed ignore file of the project or a declared pattern
covers it. A file ignored by a personal rule (the user's global excludes file, or the repository's
info/exclude) was hidden by a person for their own reasons, and it is an untracked file like any
other. So is a loose ignored file that is in no build output folder, such as a local settings file:
git's non-forced worktree remove deletes it without a word, so rule 5 has to see it first. Measured on
this repository's 79 worktrees on 2026-11-13: two hold such a file, so the rule costs two requests
there.

A git repository is treated as one wherever it is found, whatever kind its item was declared as. A
worker clone, a batch clone and a candidate workspace are repositories with commits of their own, and
the first design removed them as scratch. They are never declared and never adopted as scratch. Each
is an item of the kind agent repository, the one kind a private repository has (section 5), and goes
only after the keep step, like any worktree.

The look of rule 6 starts at the item's own folder, not beneath it. An item whose folder is a git
repository (it holds a .git entry, or is itself a git folder) and whose kind is neither worktree nor
agent repository holds itself, as unrecorded. So a clone that a creator or a reconcile rule still
called scratch stays where it is, and the deferral says why.

A repository found beneath a scratch folder or a build output folder holds that folder as one beneath
a worktree does (section 7, "A nested repository holds its worktree"), with one exception: a clean
clone. That is a repository for which all of these are read and found true at the attempt:

- it has no uncommitted and no untracked file, and no stash;
- every ref and its HEAD is held by one of its own remote-tracking refs;
- no entry of its HEAD log or of a branch's log names a commit that those remote-tracking refs do not
  reach. A reset leaves such a commit named by a log alone, and 0.2 keeps log commits for that reason;
- for a remote whose address is a path on this host, each of those commits is in that repository
  now. A remote-tracking ref says what the remote had at the last fetch, and any process of the
  owner's can write one, so the ref alone is not taken for a local remote.

Everything in such a repository has already been pushed somewhere, and a build that fetched it will
fetch it again. A repository that cannot be read is not a clean clone, and neither is one whose local
remote cannot be read. For a remote on another host the ref is all that can be read without the
network, and 0.9 names what that leaves.

A bound repository and a plain repository are never items. Space management removes worktrees, private
repositories and folders, and never a repository a person works in. Veldo has no branch remover (a
contained branch is marked and kept), and if one is ever added, a branch is removed like anything else
here: its commit goes to a kept ref first.

### 0.2 Commits: recorded on a kept ref before anything is removed

Before a worktree, a branch or a private repository is removed, every commit that can be reached from
it is on a kept ref in its main repository. A ref at a commit keeps that commit and everything before
it, so one ref per tip is enough. This is the keep step. It runs after rules 1 to 6 have passed and
before the tool of rule 7 is called, at every removal of a worktree or a private repository, with no
test of whether some other ref already holds the commit. A test that can be wrong is how a stash once
hid an unlanded commit; a write that always happens cannot be wrong that way, and one more ref costs
nothing.

The name is refs/veldo/kept/<ticket>/<item>/<what>:

| Part | Content |
| :- | :- |
| ticket | The item's ticket. For an item with no ticket: run- and the run's label when a run owns it, otherwise the word none |
| item | The item's identifier in the ledger |
| what, for a worktree | head for the checked-out commit; ref/ and the name for each of the worktree's own refs (a bisect, a rewritten ref); op/ and the name for each commit an operation in progress names (ORIG_HEAD, MERGE_HEAD and the like); log/ and a number for each commit that only the worktree's HEAD log names |
| what, for a private repository | ref/ and the full name for every ref it has, branches, tags and remote-tracking refs alike; stash/ and a number for every stash entry, not the newest alone; head for its HEAD; log/ and a number for each commit only a log names |

Uncommitted changes get no ref. They are saved outside git (0.3).

Every character git refuses in a ref name is replaced by '-', as section 6.5 does for a kept branch.

The log entries are there for a measured reason. On git 2.43.0 a commit made in a detached worktree
and then left behind by a reset is named only by that worktree's HEAD log. A person gets it back today
with git's reflog command. After git's worktree remove the log is gone and nothing names the commit.

How it is written. For a worktree the commits are already in the main repository's object store, and
the step is one ref write per tip, which names the event in the ref's own log. For a private
repository the step first brings the objects across with git's fetch from the repository's path into
the main repository, naming every ref, and by hash for stash entries and log commits (measured on git
2.43.0: a fetch by hash from a local path works when the call sets uploadpack.allowAnySHA1InWant for
itself). The fetch follows no tag by itself, recurses into no submodule, and checks every object it
receives. Each ref is created and never moved: a name that already exists at the same commit is left,
and one that exists at another commit is a failure.

An agent's worktree is written the second way. Its commits are in the agent repository's object
store, and that repository is removed after it. So the step fetches the worktree's tips from the
agent repository into the shared repository and writes the kept refs there, under the worktree's own
item, and the keep record names the shared repository. Nothing is written under refs/veldo/kept in an
agent repository. The first form of this section wrote them there. The agent repository's own keep
step then carried them across under its own item's name and they went with the repository, so the
listing showed the worktree's refs as lost and a restore of the worktree found no head. An agent's
worktree whose agent repository names no shared repository cannot be kept, and stays.

Then the step reads every ref back and compares it with the commit it meant to write. Only then does
it write the list of refs and commits on the item's record, as one journal record, and only after that
record is committed does the remover run.

When any part of that fails, the removal does not happen. The item is deferred as keep_failed, with
the ref and what git said, and everything is still where it was. The same holds for a private
repository whose main repository the declarations do not name: it cannot be kept, so it stays. And it
holds for a worktree or a private repository whose main repository is no longer at its path, because
someone moved or deleted it: the step has nowhere to write, the item is deferred as keep_failed, and
no path removes it, reconcile's completion and its acting on a past event included.

Kept forever. No command, event, mode or reconcile of Veldo deletes or moves a ref under
refs/veldo/kept. The one way a kept ref goes is the owner's own signed command (0.5). The boundary
check (6.2) treats a ref delete, a stash drop or clear, a reflog expire and a prune of objects as
removal primitives, and refuses each one outside that command. Git's own garbage collection does not
remove what a ref reaches, so the commits stay for as long as the refs do.

What a kept ref is not. It is not a branch: nothing builds from it, nothing lands from it, and the
reference-transaction hook sends nothing for it (6.9). It is not a reason to remove: rule 5 does not
count a kept ref among the refs that hold a commit, as it does not count a stash, so writing kept refs
never turns unique work into no unique work. Veldo never pushes it, and git's ordinary push and clone
do not carry it.

A crash between the steps loses nothing, whichever step it falls on:

| The process dies | What is on disk | What the next attempt or reconcile does |
| :- | :- | :- |
| Before the refs are written | Everything, untouched | Starts again from rule 1 |
| After the refs, before the record | The refs and the item | Finds each ref at the same commit and passes; writes the record |
| Inside the snapshot write, where the removal writes one (0.3) | The refs, the item untouched, and a folder with a temporary name in the snapshot store | Starts again from rule 1 and writes a new attempt under the next number. The temporary folder stays, is counted in the console's totals and is reported by reconcile |
| After the snapshot's rename, before the record | The refs, the item untouched, and a whole snapshot folder that no keep record names | The same: a new attempt under the next number. The folder no record names stays, counted and reported |
| After the record, before the remover | The refs, the record, the snapshot it names, the item | The next attempt, or reconcile reading the record from the ledger, starts again from rule 1. It uses the snapshot the record names when that still has the recorded digest and the item still equals it, and otherwise writes the next attempt and adds it to the record. Then it removes |
| Inside a remover that deletes file by file, stopped by a file that changed | The refs, the record with the attempt that holds every file, and what is left of the item, back at its locator (0.3, 6.5) | The next attempt saves what is left under the next number and adds that attempt to the record. The first attempt stays on the record, and a restore applies both (0.3, 0.5) |
| Inside the remover | The refs, the record, and a folder half removed under its marked name, or a worktree git has partly removed | Reconcile completes it, and only because the record is there and every ref in it still resolves (4.1, 8.8) |
| Inside a Discard or a Save, after the worktree was moved to its marked name | The refs, the record with its snapshot, and the whole worktree under its marked name | Reconcile sets git's record of the worktree right with git's worktree repair and reads the worktree again. Equal to its snapshot and not in use, its removal is completed. Otherwise it is moved back to its path and deferred as keep_failed (0.3, 8.8) |
| After the remover, before the outcome | The refs and the record | Reconcile finds nothing at the locator and writes the outcome |

Section 4.1 said a removing item "is removed to the end, because the decision to remove it was already
made and recorded". That now needs the keep record as well: reconcile completes a removing worktree or
private repository only when its keep record exists and each ref in it resolves to its commit.
Otherwise the item is deferred as keep_failed and what is left of it stays.

### 0.3 Uncommitted, untracked and stashed changes: only the owner's Discard, and Discard saves first

Changes that are in no commit are never removed before they are saved. In a worktree they are also
never removed without the owner's explicit Discard, with one exception, a review's scratch. Nothing
else in Veldo deletes a tracked edit, a staged change or an untracked file that is work: every other
removal of a worktree uses git's non-forced remove after rule 5 has refused for each of them (section
7).

Discard itself no longer loses them. Before the forced remove runs, the discard remover writes a
snapshot of the worktree's uncommitted state, reads it back, and only then removes. So a Discard can
be undone (0.5). Section 7 said the request's terms "state that Discard cannot be undone"; they now
state what Discard removes from disk, that it is saved first, and the command that brings it back.

Where a snapshot is stored (the lead's decision, 2026-11-13): outside git, in the snapshot store, a
folder under the Veldo state root, and never in a repository's object store. The reason is secrets. An
ignored local settings file is the kind of file a snapshot saves, and it may hold a key. Stored as a
commit, that key would be in the main repository's object store, where the secret scanner reads it and
where every agent repository reads it through its alternate. Stored as a file under the state root it
is where the worktree's own copy was: on the owner's disk, in a folder only the owner's account opens.
The first form of this section made the snapshot a commit in git's stash layout on a kept ref. That is
withdrawn. Commits stay on kept refs (0.2); what was never committed goes to the snapshot store.

One folder per attempt, under the item's own folder, which is named as the item's kept refs are. The
store and every folder in it have mode 0700:
<state root>/space-saved/<ticket>/<item>/<n>/

n is 1 for the item's first snapshot and the next unused number for each later one. A folder that has
been written is never written again, never replaced and never deleted, by a retry or by anything else
but the owner's drop command. An item gets a second snapshot when a Discard was deferred because the
worktree changed after the first, and when a crash stopped an attempt before its keep record was
written. A rename onto the first folder would fail, and deleting the first to make room would leave a
moment with no copy at all, so neither is done.

| Entry | Content |
| :- | :- |
| manifest.json | The item, its ticket, its main repository, the path it had, the checked-out commit and the event. One row per saved path: what it is (a tracked edit, a staged state, an untracked file, an ignored file that is work), its mode, its size and its SHA-256. The tracked paths deleted in the worktree, and those deleted in the index |
| work/ | Each tracked file that differs from the checked-out commit, each untracked file and each ignored file that is work, at its own path, byte for byte. A link is saved as a link |
| staged/ | For each path whose staged content differs from the working file, the staged content |

It is written without touching what it saves, and git writes nothing for it. The remover reads the
lists with git's status and ls-files and the staged contents with git's cat-file, and copies the files
itself. None of those commands adds an object. (A file someone staged is already an object in the
repository, by their own git add; the snapshot adds none.) It does not run git's stash command, which
would empty the worktree before anything is saved and would write to the stash stack every worktree of
the repository shares.

The snapshot is written under a temporary name beside its place, <n>.partial. Each file is then read
back and its digest compared with the manifest's and with the worktree's file, every file and the
folder are synced to disk, the folder is renamed to <n>, and the item's folder is synced so that the
rename itself is on disk. Only then does the keep record get the snapshot's path with its number, its
size and the digest of its manifest. The Ledger reads that digest from the manifest itself before it
writes the record (6.1).

The forced remove then runs only while the worktree still equals the snapshot. The remover reads the
worktree's state once more after the snapshot is in place, and a file that was added or changed in
between stops the remove; the worktree is deferred again and the request is raised again with the new
list. That is the check section 6.5 already makes against the list the owner was shown, made a second
time against what was saved.

The last look and the remove have no moment between them (the final check, 14.8, F4). Reading the
worktree once more and then running one git command leaves a gap. Rule 4 has run by then, so only a
process that starts in that gap can write there, but a file it writes would go with the Discard
unsaved. So the discard remover first renames the worktree to a marked name beside itself, as the
folder remover does with a folder (6.5). The rename is git's worktree move, without the force
option, which keeps the worktree and the repository's record of it pointing at each other. Under the
marked name the remover runs the in-use probe again and reads the worktree's state again, and it
removes only when no user is found and the worktree equals the snapshot path by path, in mode and in
digest. A process that writes by the worktree's path after the rename finds no such folder: the
write fails in the writer's own hands, and no file that was written is lost. A file written before
the rename is seen by the look that follows it. When that look finds a user or a difference, the
worktree is moved back to its path and deferred as keep_failed with everything in it, and the
request is raised again with the new list.

When git refuses the move, as it does for a locked worktree and for one that holds a submodule,
nothing has been renamed, and the worktree is deferred as remove_refused at its path. Where a crash
left the folder under its marked name while git's record still names the old path, or the other way
round, git's worktree repair, run in the folder, sets the record right before anything else is done
(8.8). Something that appears at the old path while the worktree is under its marked name is not
the worktree, and no remover touches it. When it is in the way of the move back, the worktree stays
under its marked name with its item removing, and reconcile reports both. Neither was measured on
this host for this amendment; ticket 0318's rows show them.

A save that fails, or that stops half way, refuses the removal. Each of these ends the attempt with
the item deferred as keep_failed and everything in it still in place: the store cannot be made or
written; the store's pool runs out of room, also in the middle of a file; a file of the item cannot be
read; a write comes back short; a read back differs from the manifest or from the item's file; a sync
fails; the rename fails; the Ledger refuses the keep record. The remover is called only after the keep
record that names the snapshot is committed, so there is no order of these in which a removal follows
a save that did not finish. What a failed attempt wrote stays under its temporary name. It is not
deleted, because a remover that deletes in the snapshot store is the one thing the store is protected
from, and the next attempt takes the next number.

A retry is idempotent. However many times an attempt is made, by a next event, by reconcile or after
a crash, the result is the same: the item is removed at most once, the keep record lists every
attempt it was given, and every attempt ever written is still in the store. A retry starts from rule
1. It finds each kept ref at the same commit and passes (0.2). For the snapshot it first looks at the
newest attempt the keep record lists, when there is one: when the manifest still has the recorded
digest and the item equals the snapshot path by path, in mode and in digest, it uses that attempt and
writes nothing. In every other case it writes the next number and adds that attempt to the record. A
crash between the save and the removal is recovered the same way, and what tells reconcile to do it
is the ledger: the item is due or removing, its keep record lists a snapshot, and the item is still
whole at its locator (0.2's table, 8.8).

The keep record lists attempts, and no later write takes one off the list. Until the final check
(14.8) the record named one snapshot, and a later save wrote the record again. That loses work when a
removal that deletes file by file stops part way. A review worktree holds scratch files a and b. The
first attempt saves both, deletes a, finds b rewritten and stops, as it should. The retry finds that
the worktree no longer equals the first snapshot, saves b alone under number 2, and removes the rest.
With one snapshot in the record, a restore applied number 2, did not bring a back, and said success.
So the record's snapshot field is a list: one entry per attempt, with its path, its number, its size
and its manifest digest. A keep write for an item that already has a record adds refs and attempts
and removes none. That holds for a write that saves nothing as well: the worktree's own non-forced
remove after its review scratch has gone, and Save's remove after Save's snapshot, leave the list as
it was. An attempt whose write failed, and one that was whole but never reached the record, are not
on the list. No delete followed either of them, so the item still held everything they saved.

An operation in progress is saved as its files and the commits it names (the op/ refs of 0.2); the
state of the operation itself is not rebuilt by a restore.

A snapshot is kept as a kept ref is. No command, event, mode or reconcile of Veldo deletes or changes
anything in the snapshot store. The store is on the protect list of every installation, put there by
the Ledger and not by a file, so rule 2 refuses any removal at, above or beneath it, and reconcile
records and proposes nothing in it. The one code path that deletes there is the owner's drop
command (0.5). So the store grows with every snapshot, as the kept refs grow with every removal (the
lead's answer on growth): the console shows how many of each there are and how much space they take
(section 10), and nothing drops one without the owner's rule. The totals count every folder in the
store: the snapshots keep records name, the attempts no record names, and the temporary folders a
failed or killed attempt left.

The store is watched, and its loss is never silent. The protect list and the boundary check bind
Veldo's own code. They do not bind a process of the owner's account, and an agent outside the sandbox
is one: it can delete the store, or delete a kept ref and let git collect the commits. Veldo cannot
stop every way of doing that (0.9), so it looks for it. Reconcile, at every service start and whenever it is asked, and
veldo space kept, each time it is run, check every keep record against the disk: each kept ref
resolves to the commit the record names, every snapshot attempt the record lists is there, and each
manifest has its recorded digest. A restore makes the same check for its item before it writes
anything (0.5). Whatever fails is reported under space.reports as kept work missing, with the item,
the ticket, the path the item had and what is missing. The console shows the report at the top of the
Space screen and on the overview, and it stays until the ref or the snapshot is back or the owner
drops that item's kept work. A store folder that is missing as a whole, or whose owner or mode is not
the installation owner's and 0700, is one more report of the same kind. The keeper also looks each
time it writes a snapshot: a store that is gone while keep records name snapshots in it is reported
before the new one is written. A snapshot's folders that no keep record names are listed in the same
read as information, with their sizes; nothing is proposed for them. They are not left to grow
unseen (the final check, 14.8, F4). Each one, whole or temporary, is listed under the item whose
folder in the store holds it, it is counted in the totals, and it goes with that item's drop, which
lists its files before it acts (0.5).

The guard keeps an agent's own commands off the store and the kept refs (the lead's decision,
2026-11-13; VELDO-0349). The guard hook, scripts/veldo-guard.sh, already reads every shell command an
agent is about to run and refuses some of them. It gains one rule: a command whose text names the
snapshot store or refs/veldo/kept is refused before it runs, and the refusal says why and names veldo
space kept, veldo space restore and veldo space kept drop. The store is named by its path under the
state root, written in full or with the home folder written as ~ or $HOME. The guard takes the state
root from where the keeper takes it. When it cannot read it, it refuses any command that holds the
word space-saved.

One command passes even when it names them: veldo space kept drop, as the whole command with nothing
joined to it. Letting it through is safe because the Ledger refuses a drop the owner did not sign
(0.5). veldo space kept and veldo space restore name an item and not the store, so the rule does not
touch them; restore's option ref takes the short name the listing shows, not the full ref name. A
command that names neither the store nor the kept refs is judged exactly as before.

The rule refuses reading as well as deleting, and it refuses a mention: a commit message that quotes
the ref name has to come from a file. It reads the text of a command and nothing else. So it does not
stop a program the agent writes and runs, a path put together from a variable, or a link that points
at the store. The watch above stays for those.

Save is unchanged for tracked and untracked source files: they are committed on a kept branch by the
owner's answer. Ignored files that are work do not belong on a branch, because the project said they
are not source and they may hold a secret. Save writes them to the snapshot store before the worktree
goes.

Save then removes the worktree by git's non-forced remove, which deletes ignored files without a
word, and rule 5's case 3 refuses a worktree that holds an ignored file that is work. Left like that,
Save could never finish, or would have to skip the rule and lose an ignored file written after the
snapshot. So before Save's remove the remover reads the worktree's ignored files that are work once
more and compares them with the newest snapshot the keep record lists, by path, mode and digest. Rule 5's
case 3 counts as saved exactly the files that are in that snapshot and unchanged, for this one remove
and for no other. A new ignored file, a changed one, or any other case of rule 5 refuses the remove;
the worktree is deferred with everything in it, and the next attempt saves again under the next
number.

Save's last look is made under a marked name too, as Discard's is (above). Git's non-forced remove
refuses a tracked edit or an untracked file by itself, but it deletes an ignored file without a
word, and that is the file a gap between the look and the remove would lose with no trace. So the
worktree is moved to its marked name first, and the in-use probe, rule 5 and the comparison of the
ignored files that are work with the snapshot are made there. A user or a difference moves the
worktree back to its path and defers it.

Two removals save and then remove with no answer from the owner. Both are the lead's decisions, and
both rest on the same sentence: saved means not lost.

Review scratch (section 7, "Review worktrees", the lead's decision (e), confirmed 2026-11-13). The
review scratch remover writes the same snapshot before it deletes a path. Nothing asks the owner.

A worker clone of a run that has ended (the lead's answer of 2026-11-13). A worker clone is a private
repository made for one dispatch. When its run is dead and its work tree still holds uncommitted or
untracked files that are work, the first form of this section deferred it as unique work and raised
one request per clone. Now the keep step records its commits (0.2), the same snapshot saves its
uncommitted state, and the clone is removed with no request. The answer names worker clones. A batch
clone, a candidate workspace and an agent repository with such files still wait for the owner, as
before.

Neither of the two has an owner who looked at a list, and neither is one git command: the review
scratch remover deletes path by path, and the folder remover deletes a clone file by file. A file
written between the snapshot and its own delete would go unsaved, and rule 4 does not see a process
that wrote it and closed it. So both removers compare each file with the manifest immediately before
they delete it: its path is in the manifest, and its mode and SHA-256 are the ones recorded. A file
that is not in the manifest, or differs from it, stops the removal there. The item is deferred as
keep_failed, what is left of it stays, and what was already deleted is in that attempt's snapshot. The
attempt stays on the keep record whatever a retry saves, and a restore brings its files back.

What is left stays at its own path (the final check, 14.8, F3). The folder remover has renamed the
folder to a marked name before the first delete, and until this amendment it renamed it back only
when its second probe found a user. A stop by the comparison left a worker clone's folder under the
marked name. The item then had nothing at its locator, reconcile marked it gone, and the one file
that was not saved sat in a folder no item names: nothing deleted, but nothing a restore by the
item's id could reach. So on that stop the remover renames the folder back to the path it had
before it defers the item. That holds for a worker clone's folder and for a folder of review
scratch alike. The item keeps its id and its locator, the next attempt saves what is left under the
next number, and a restore then brings every file back. When the rename back fails, the item stays
removing. Reconcile looks for the marked name before it marks any item gone, so it finds the folder,
tries the rename again and reports it (8.8).

For a folder of review scratch the comparison is made for each file in it. For a
worker clone it is made for each file of the work tree that is work; the clone's git folder is
covered by the kept refs and the read back of 0.2.

"Veldo never commits on its own" now holds with no exception: a snapshot is files in a folder and not
a commit.

Stashes. A stash made in a worktree of a shared repository lives in that repository, and removing the
worktree does not touch it; no remover reads or writes a shared repository's stash. A private
repository's stash entries would go with it, so they are unique work under rule 5, the repository
waits for the owner's answer, and whichever answer removes it writes every entry to a kept ref first
(0.2). A stash entry is a commit its author made with git, so it is kept as a commit and not in the
snapshot store.

### 0.4 Evidence, and what the owner marked Keep

Evidence is never declared as scratch. The receiver's artifacts, receipts and token records, gate logs
and stamps, review reports and proof bundles are items of the kind evidence, and the table of section
5 keeps them. The one removal that table allows is, at a ticket's or a project's end, a file "whose
digest the store or the landed commit already holds". Under this rule that means: the remover reads
the file's digest again at the moment of the removal, and removes the file only when the store holds
a blob with that digest, or a commit that the trunk or a kept ref reaches holds a file with it. A
digest recorded at an earlier measurement is not used, because the file may have changed since. A
store or a commit that cannot be read means no copy, and the file stays.

Keep. An item in state kept is never made due, and no event, retry, Confirm, reconcile or outside
cleaner's question removes it or offers it. It holds whatever it is inside (section 7, "A child holds
its parent"), so a kept worktree keeps its agent repository and a kept evidence folder keeps its
worktree. Only the owner's Abandon ends Keep, and an abandoned item then meets every rule again, this
section included. A keep entry in a project's space file and an entry of the protect list are the
same promise made in a file.

### 0.5 Getting it back

Every removal of a worktree or a private repository leaves its kept refs, and the item's record lists
them with the path the item had. The owner needs one command:

| To | Command |
| :- | :- |
| See what was removed and what was kept for it | veldo space kept, for everything; veldo space kept and a ticket, an item or the path the item had, for one. For each item it says whether every kept ref still resolves to its commit and whether the snapshot is still there and whole, and it reports what is not (0.3) |
| Get a removed worktree back | veldo space restore and the item, or the path it had. It adds a worktree at that path at the kept head, on its branch when the branch still points there and is checked out nowhere, otherwise detached, and applies the saved snapshot when the keep record names one: it checks the manifest against the digest the record holds and every saved file against the manifest, copies the working files in with their modes, removes the tracked files the manifest lists as deleted, and stages what was staged. An untracked or ignored file is copied and never added to git. The option to and a path puts it somewhere else |
| Get a removed worker clone's uncommitted files back | The same command and the clone's item. It adds a worktree at the clone's kept head and applies the clone's snapshot |
| Get one commit of a removed private repository back | veldo space restore, the item, the option ref and one of the names the listing shows. It adds a worktree at that commit |
| Let kept work go | veldo space kept drop and the item. It lists every commit that would no longer be reachable and every file of every attempt folder of the item with the size, the folders no record lists and the temporary ones included, and removes the refs and the item's whole folder in the store only on the owner's signed command. No host principal may send it |

Restore never overwrites: it refuses when something is at the path. It leaves the kept refs and the
snapshot where they are, so a restore can be repeated. It is the owner's signed command, and what it
makes is recorded like any worktree added by hand.

A restore that cannot find or verify its snapshot fails loudly. Whether an item has a snapshot is
read from its keep record and from nowhere else, never from what happens to be on disk. The record
lists each attempt's folder and the digest of its manifest. Restore applies every attempt on the list,
the oldest first, so that where two attempts hold the same path the later one wins. Before it adds the
worktree it checks all of this for every listed attempt, and it refuses, with exit status 1 and the
item and the reason in words, when any of it fails for any of them:

- the snapshot folder the record names is there, and its manifest is in it;
- the manifest's digest is the one the record holds;
- every file the manifest lists is there, with the size, mode and digest the manifest gives;
- no path in the manifest is absolute, holds a ".." part, or resolves outside the target path, also
  through a link that is already in the snapshot or in the new worktree.

A refused restore adds no worktree and changes nothing, and it writes the report of 0.3: kept work
missing, with what is missing. It never adds the worktree at the kept head and calls that a restore.
The owner who wants the commits alone, knowing the snapshot is gone, names a kept ref with the option
ref. That adds a worktree at the commit, applies no snapshot, and says so in its output. When the
record names no snapshot, because the removal needed none, restore says that too. A kept ref that no
longer resolves refuses the same way.

Restore's output names the attempts it applied. A file that only an earlier attempt holds comes back,
also when the owner had deleted it from the worktree between two attempts. Of the two mistakes a
restore can make, bringing back a file too many is the cheap one.

The same with plain git, when Veldo is not running. The names say what they hold:

```
git for-each-ref refs/veldo/kept
git worktree add <path> refs/veldo/kept/<ticket>/<item>/head
cp -a <state root>/space-saved/<ticket>/<item>/<n>/work/. <path>/
```

The third line is a plain copy, because a snapshot is ordinary files. It is run once for each attempt
the keep record lists, the lowest number first. Without the ledger that is every numbered folder of the
item that has no .partial ending, in order, and each manifest says what it holds. It brings back every
working file. The staged contents are in the
snapshot's staged folder and the deleted paths are in its manifest, for the owner to apply by hand. The
first form restored a snapshot with one git command; that is the price of keeping snapshots out of git,
and the lead took it.

The listing does not depend on the ledger. The refs carry the ticket and the item in their names, and
each ref's own log holds the event that wrote it, so the first of those three lines answers "what was
kept" from the repository alone. The snapshot folders carry the same ticket and item in their path,
and each manifest says what it holds. The console's Removed section shows, for each removal, how many
refs were kept, whether a snapshot was saved and its size, and the restore command with the item
filled in. Above the list it shows the totals: how many kept refs and how many snapshots there are,
and the size of each.

Evidence needs no restore, because it is not removed. Build output and scratch have none, because they
are not work.

### 0.6 Every probe and every rule fails closed

A question a probe or a rule cannot answer is answered against the removal. Section 7 ("What a probe
cannot read") holds the cases the reviews found. This section adds the ones the rule itself creates,
and they follow the same line:

| What cannot be read or done | The answer |
| :- | :- |
| A kept ref cannot be written, or reads back as another commit | keep_failed; nothing is removed |
| A private repository names no main repository, or an agent's worktree whose agent repository names none | It cannot be kept; it stays |
| The main repository is not at its path any more | keep_failed; nothing is removed, by an event or by reconcile |
| The snapshot cannot be written, synced, read back or renamed into place, or the store has no room or cannot be written | keep_failed; the discard, Save's remove, the scratch removal or the clone's removal does not run, and what the attempt wrote stays |
| The item changed after its snapshot: a worktree before the forced remove, an ignored file before Save's remove, a file of review scratch or of a worker clone before its own delete | keep_failed; the removal stops there |
| A removal the comparison with the manifest stops inside a folder the remover renamed | The folder is renamed back to its path before the item is deferred. Where that fails the item stays removing, and it is never marked gone |
| A worktree that is in use or has changed when it is read under its marked name, before a Discard's or a Save's remove | Moved back to its path; keep_failed, and nothing is removed |
| git refuses to move the worktree to its marked name | remove_refused; the worktree stays at its path |
| An item with nothing at its locator and a folder or a worktree under its marked name beside it | Not gone. Reconcile completes it only as 8.8 says, and otherwise moves it back |
| A snapshot folder already exists for the item | It is left as it is; the attempt writes the next number |
| The item's keep record already lists a snapshot attempt | It stays on the list; the new attempt is added to it |
| At a restore, any snapshot attempt the keep record lists has its folder or manifest missing, a manifest's digest is not the recorded one, a saved file does not match the manifest, or a manifest path leads outside the target | The restore is refused and says why; nothing is added, the snapshot stays, and kept work missing is reported |
| A kept ref that does not resolve to its recorded commit, or a snapshot that is missing or not whole, found by reconcile or by veldo space kept | Reported as kept work missing until it is back or the owner drops it. Never passed over |
| A repository beneath scratch or build output whose logs, or whose local remote, cannot be read | Not a clean clone; it holds the item |
| An item of a kind other than worktree and agent repository whose own folder is a git repository | It holds itself |
| An ignored path that no committed ignore file and no declared pattern covers, or whose rule cannot be traced | Untracked work; rule 5 refuses |
| A folder beneath a scratch or build output item that cannot be listed, or a repository there that cannot be read | It holds the item |
| An evidence file whose copy cannot be found or read at the removal | No copy; the file stays |
| A removing item with no keep record, or with a kept ref that no longer resolves | Not completed; deferred as keep_failed |
| A list of children, or a look, that a caller hands in | Not trusted; each rule looks for itself at the attempt (section 7) |
| The switch to act with no proof record for the space modules now installed (0.7) | Refused; and a scope already in act removes nothing until there is one |

The direction is always the same one. A wrong answer may cost space, a deferral or a request. It may
not cost work.

### 0.7 The suite that proves it, and act mode

One ticket, VELDO-0348, is a suite whose only question is whether work was lost. It plants work, drives
a removal path at it, and then looks for the work. A row passes when every planted thing is still in
its place byte for byte, or comes back byte for byte through veldo space restore from what the removal
left. A copy the suite kept for itself proves nothing and is not looked at.

It drives every removal path this design has: git's non-forced worktree remove at each ending event;
the review scratch remover; Save; Discard for one worktree, for a group and for one member; the agent
repository remover on an agent repository, a worker clone, a batch clone and a candidate workspace,
each declared by its creator and each adopted by reconcile; the folder remover on scratch, build
output, a run directory and a sandbox launcher's scratch; the evidence removers; veldo space restore
after each removal that left something; Confirm
in report mode; the retries by admission and by a retirement; reconcile's completions and its acting
on a past event; the Docker removers, with a bind mount into a worktree; and the answer the ledger
gives an outside cleaner.

At each it plants every kind of work of 0.1: a commit on a detached HEAD, a commit only the HEAD log
names, a commit on an unlanded branch, a commit under a worktree's own ref and one an operation in
progress names, a tracked edit, a staged change, an untracked file, an ignored file that is not build
output, a stash entry in the shared repository and two in a private one, a branch and a tag the shared
repository does not hold, an evidence file and a proof file with no copy, and an item the owner marked
Keep. The planted ignored file holds a marker. After each drive the suite searches the object store of
every repository it made for that marker, and finding it there fails the row.

And in each of these shapes:

| Shape | What is planted |
| :- | :- |
| Nested | A repository in an ignored folder, in build output and in scratch; a worktree inside an agent repository; a submodule; kept evidence inside a worktree; a scratch item whose own folder is a repository; a clone in scratch whose only unpushed commit is named by a log, and one whose remote-tracking ref names a commit its local remote does not hold |
| Adopted | A batch clone with an unpushed commit on a branch, and one with it on a detached HEAD, that no item records; its batch has ended and the scope is in act; reconcile adopts it and acts on the past event |
| Agent worktree, then its repository | An agent's worktree is removed, then its agent repository, then the worktree is restored |
| Linked | A link in the place of the item's folder; a link inside it that points out, and one that points in; an item whose path goes through a linked folder |
| Locked | A worktree git has locked; an index lock; a held scratch lock |
| Unreadable | A folder of mode 000; a repository git refuses to read; an engine that cannot be read; a process table that hides processes; a main repository that cannot be written |
| Main repository gone | A worktree, and a private repository, whose main repository was moved, and one whose main repository was deleted. Each ending event and each reconcile path is driven at it |
| Snapshot store | A store whose pool fills in the middle of a file; a store that is not writable; a read back that differs; a rename that fails; a sync that fails |
| Retry | A snapshot folder that already exists for the item, whole, and one left under its temporary name; the attempt is made again, and again after that. A review worktree whose scratch removal stopped after its first delete, is retried, and is then restored |
| Restore | The snapshot folder deleted; the manifest deleted; the manifest changed; one saved file changed; a manifest path that is absolute, one with a ".." part and one that leads out through a link; a kept ref deleted |
| Mid-removal | A file added after the probe; a process that opens a file after the first probe; a branch that moves between the probe and the remove; a file added between the snapshot and the forced remove; an ignored settings file added between Save's snapshot and its remove; a file of review scratch, and a file of a dead run's worker clone, rewritten between the snapshot and its own delete; a file written by the worktree's path between the last look and git's remove, in a Discard and in a Save; a worker clone whose removal the comparison stopped, with reconcile run afterwards |
| Crash between steps | The process is killed at each boundary of the table in 0.2, the two snapshot boundaries included, and at each step of the folder remover, and reconcile then runs |

The suite has to be able to fail. Each loss the reviews reproduced, and each step this section adds,
is a mutation that must turn a row red: a kept child that does not hold its parent, a stash counted
as a holding ref, no look beneath a worktree, a private repository compared with itself, an unreadable
worktree read as unlocked, an unopenable scratch read as free, the keep step skipped, the remove run
after a failed keep, Discard without the snapshot, a snapshot written into a repository's object store,
and a removing item completed with no keep record. The validation of this section added ten: the
remove run after a failed snapshot, review scratch deleted without the snapshot, a file deleted
without the comparison with its manifest, an existing snapshot folder replaced on a retry, Save's
remove run with an ignored file the snapshot does not hold, a restore that applies the snapshot only
when its folder is there, a clone adopted as scratch, no look at an item's own folder, an agent
worktree's kept refs written into its agent repository, and a clean clone read without its logs. The
final check (14.8) added one: a keep record that holds only the newest attempt. Its points F3 and
F4 added two: a folder left under its marked name when the comparison stops its removal, and a
Discard or a Save that removes the worktree at its own path.

A row that restores passes only on the command's own word and the files together: restore said it
succeeded and every planted file is back, or restore refused and said what is missing. A restore that
reports success with a planted file absent fails the row.

It is a condition of act mode. The suite runs in the gate like every other. It also has a host form,
veldo space prove, which the owner runs on the host that will remove: the same rows against that
host's git and filesystem, in a scratch root of its own, with repositories and a ledger it makes for
itself and Docker objects only under its own label. A pass writes one proof record (4.10) with the
digest of the space modules, git's version and the day.

The switch to act is refused until four things are true, and the refusal names each one that is not:

1. the scope's three clean report days (VELDO-0332);
2. no unconfirmed pending group, and the space steps in the project's gate (VELDO-0339);
3. the process reader's ticket landed (VELDO-0344, 7.1). Whether the reader is installed is read by
   the probe at each attempt, and without it unread processes are judged by the bound;
4. a proof record that passed, for the space modules installed now and the git in use now (VELDO-0348).

Until VELDO-0348 lands the ledger refuses every switch to act as space_act_unbuilt and names it, as it
names VELDO-0332 and VELDO-0339 today. After an upgrade of the modules or of git the proof record no
longer matches. No new switch to act is then accepted, and a scope already in act behaves as in report
mode: its events write due and remove nothing, and the console says why, until the owner has run
veldo space prove again. Nothing counts days here and nothing switches a mode by itself; the record is
read when an event or a command needs it.

### 0.8 What this changes in the tickets

Every ticket, VELDO-0296 to VELDO-0344, was read against the rule. Four tickets are added, VELDO-0345
to VELDO-0348 (section 12). The tickets whose acceptance criteria change:

| Ticket | Criterion | The change |
| :- | :- | :- |
| VELDO-0302 Creators | AC1 | A clone, a batch clone and a candidate workspace are declared with their main repository. Artifacts, receipts and token records are declared as evidence and never as scratch |
| VELDO-0304 Boundary check | AC2 | A ref delete, a stash drop or clear, a reflog expire and a prune of objects are removal primitives, refused everywhere but the owner's kept drop command |
| VELDO-0305 Census | AC1, AC2 | An ignored folder is build output only when a committed ignore file or a declared pattern covers it. An ignored path nothing of the project covers, and a loose ignored file, make the worktree unique work |
| VELDO-0315 Reconcile | AC2 | A removing worktree or private repository is completed only when its keep record exists and every ref in it resolves; otherwise it is deferred as keep_failed |
| VELDO-0318 Unique work at a ticket's end | AC2, AC3 | Save writes ignored files that are work to the snapshot store, never to the branch. Discard writes the snapshot first, runs only while the worktree equals it, and does not run when the snapshot fails |
| VELDO-0322 Documents | AC3 | The runbook gains the situation "getting removed work back" |
| VELDO-0327 Touchpoint | AC2 | The terms no longer say Discard cannot be undone. They say what it removes from disk, that it is saved first, and the restore command |
| VELDO-0336 A worktree a run owns | AC3 | Review scratch is saved in the snapshot store before it is deleted |
| VELDO-0340 Review groups | AC3 | A group's Discard saves each member first |
| VELDO-0343 Discard keeps every commit | AC1, AC4 | The uncommitted file is gone from disk and is in the saved snapshot. Discard makes no commit; its snapshot is files outside git |

The lead's answers of 2026-11-13 (section 13) changed criteria a second time, in the five tickets
above that name the snapshot and in the four tickets this section added. None of them is built.

| Ticket | Criterion | The change |
| :- | :- | :- |
| VELDO-0318, 0336, 0340 | AC2 and AC3, AC3, AC3 | The snapshot is in the snapshot store, outside git, where each said a saved ref or a kept ref |
| VELDO-0327 Touchpoint | AC2 | The terms say that the files are saved first, and no longer where |
| VELDO-0343 Discard keeps every commit | AC4 | Discard makes no commit at all, and the row counts the commits in the repository |
| VELDO-0345 The keep step | AC4 | The snapshot is plain files with a manifest under the state root. Writing it adds no object to any repository, and the store is protected |
| VELDO-0346 Kept, restore and drop | AC2, AC3, AC4 | Restore applies the snapshot from the store and checks it against its manifest. Drop also removes the snapshot. The console and the read show sizes and the totals |
| VELDO-0347 Work the first rules did not see | AC3 | A worker clone of a run that has ended is saved and removed with no request. A batch clone and a candidate workspace still raise one |
| VELDO-0348 The suite | AC3 | One more mutation: a snapshot written into a repository's object store |

The validation of this section (14.7) changed criteria a third time. None of these tickets is built.

| Ticket | Criterion | The change |
| :- | :- | :- |
| VELDO-0302 Creators | AC1 | The clone, the batch clone and the candidate workspace are declared as the kind agent repository, with their form and their main repository, and never as scratch |
| VELDO-0315 Reconcile | AC1, AC2 | A clone folder, a batch clone and a candidate workspace are adopted as agent repositories. A due or removing item with a keep record and the thing still whole is attempted again from rule 1. Every keep record is checked, and kept work missing is reported |
| VELDO-0318 Unique work at a ticket's end | AC2, AC3 | Save's remove runs only while the ignored files that are work equal the snapshot. Discard is refused by any failure of the save, and a retry writes a new attempt |
| VELDO-0336 A worktree a run owns | AC3 | Each file of review scratch is compared with the manifest just before it is deleted. One more falsifier: the scratch deleted without the snapshot |
| VELDO-0344 The process reader | AC1, AC5, AC6, AC7 | The writer is held by a pidfd; the reader waits for the probe to close; a row for a short output; the blob is read past replace refs; one more falsifier for the capability attribute's version |
| VELDO-0345 The keep step | AC1, AC3, AC4, new AC5 | An agent worktree's kept refs go to the shared repository. A main repository that is gone refuses. AC5 is the snapshot's failure, crash and retry paths |
| VELDO-0346 Kept, restore and drop | AC1, AC2, new AC5 | The listing says whether each snapshot is there and whole. Restore reads the snapshot from the keep record and refuses loudly. AC5 is the check of every keep record and the report |
| VELDO-0347 Work the first rules did not see | AC2, AC3, new AC5 | The clean clone reads logs and a local remote. The clones are agent repository items, and a worker clone's files are compared before each delete. AC5 is the look at the item's own folder and the adopted batch clone |
| VELDO-0348 The suite | AC1, AC2, AC3 | The new shapes and the ten new mutations of 0.7 |

The final check of that amendment (14.8) changed criteria a fourth time, and the lead's decision on
the guard hook added one ticket. None of these tickets is built.

| Ticket | Criterion | The change |
| :- | :- | :- |
| VELDO-0315 Reconcile | AC2 | A removing item is completed only when every snapshot attempt its keep record lists is there |
| VELDO-0344 The process reader | AC1 | The writer's status must also show NoNewPrivs 1 and Seccomp 2. The reader writes its header after it has locked itself and the table only after the probe's byte. One more falsifier |
| VELDO-0345 The keep step | AC5 | The keep record lists every attempt, and a later write removes none. One more falsifier |
| VELDO-0346 Kept, restore and drop | AC1, AC2, AC3, AC5 | The listing, the restore and the check cover every listed attempt, and restore applies them oldest first. Drop lists every attempt folder of the item. Three more falsifiers |
| VELDO-0348 The suite | AC3 | One more mutation: a keep record that holds only the newest attempt |
| VELDO-0349 The guard (new) | AC1 to AC4 | The guard hook refuses a shell command that names the snapshot store or the kept refs, and lets veldo space kept drop through |

The two points of that check which the seventh amendment left out, F3 and F4, changed criteria a
fifth time. None of these tickets is built.

| Ticket | Criterion | The change |
| :- | :- | :- |
| VELDO-0315 Reconcile | AC2 | An item is marked gone only when nothing is beside its locator under its marked name. A folder the comparison stops, and a worktree that no longer equals its snapshot, go back to their path. One more falsifier |
| VELDO-0318 Unique work at a ticket's end | AC2, AC3 | Save and Discard move the worktree to a marked name and make the last look there. One more falsifier each |
| VELDO-0346 Kept, restore and drop | AC5 | Folders no keep record names are listed under their item and go with its drop. One more falsifier |
| VELDO-0347 Work the first rules did not see | AC3 | The folder remover renames a worker clone's folder back when the comparison stops it. One more falsifier |
| VELDO-0348 The suite | AC2, AC3 | The write between the last look and git's remove, and the stopped worker clone at reconcile. Two more mutations |

Eight tickets are built and have proof bundles: VELDO-0296, 0297, 0298, 0299, 0326, 0330, 0331 and
0338. Their criteria are not edited, because a proof bundle answers the criteria it was written for.
What the rule asks of their code is carried by the new tickets and noted in their History:

| Built ticket | What the rule adds, and the ticket that builds it |
| :- | :- |
| VELDO-0297 Ledger | The item record gains the keep record, and the outcome removed is refused for a worktree or a private repository without one (VELDO-0345). The item record gains the form of an agent repository item (VELDO-0347). The proof record of 4.10 (VELDO-0348) |
| VELDO-0298 Kind registry | The ten kinds stay. The table gains one row, for an agent repository item whose form is a worker clone, a batch clone or a candidate workspace (VELDO-0347). The review scratch action saves first, in the remover (VELDO-0345, VELDO-0336) |
| VELDO-0299 Probes | Rule 5's case 3 counts an ignored file that is not build output, and no probe counts a kept ref as a holding ref (VELDO-0347). The clean clone reading (VELDO-0347). The in-use probe reads every thread of a process (VELDO-0344 AC8, from the validation of 7.1) |
| VELDO-0330 Rules | The keep step after rule 6 and before the tool of rule 7, inside the removers, with the deferral keep_failed (VELDO-0345). Rule 6's look beneath scratch and build output, and at an item's own folder (VELDO-0347) |
| VELDO-0331 Mode | The act refusal also names VELDO-0348, and a scope in act with no matching proof record removes nothing (VELDO-0348) |

VELDO-0296, 0326 and 0338 are not touched by the rule. Neither are the tickets not named in the first
table. They were read for a path that removes work, and each either removes nothing (0306 AC2, 0307,
0311, 0312, 0314, 0316, 0317, 0319, 0321, 0325, 0329, 0332, 0333, 0334, 0337, 0339, 0341, 0342, 0344),
or removes only through Signal and the removers the rule now binds (0300, 0301, 0303, 0308, 0309,
0310, 0313, 0320, 0323, 0324, 0335), or removes Docker objects a run's label owns (0306, 0328).
VELDO-0300 keeps its criteria because the keep step is added inside its removers by VELDO-0345, which
is built after it, and VELDO-0301 keeps its own because Signal calls those removers and no tool itself.
VELDO-0303 and VELDO-0324 keep theirs for the same reason with VELDO-0347: their criteria say that a
clone, a batch clone and a candidate folder go through Signal, and what Signal's remover does to a
private repository is VELDO-0345 and VELDO-0347. VELDO-0332 and VELDO-0339 keep theirs; their History
notes the fourth condition.

### 0.9 What the rule does not reach

The rule is about what space management removes. Seven things are outside it, and saying so is part
of the rule.

Scratch and build output are removed without being saved, because by their declaration they are made
again. A file that matters and was written into a run's scratch root, a session's scratch folder or a
build folder is lost when that folder ends. Veldo cannot tell such a file from the rest. What it can
do, it does: a repository there holds the folder (0.1), and a project names a folder it wants left
alone in its keep list (6.8). The lead confirmed this for session scratch on 2026-11-13: it goes at
the session's end, and the keep list is the tool.

A run's own Docker volumes go with the run. Data that matters is on the protect list, and an object
with no label is never removed (6.4).

The host's nightly script deletes by age and saves nothing. It is outside Veldo, it asks the ledger
before each removal while both run, and section 11 bounds how long it lives.

What the owner removes is the owner's: a kept ref dropped with the drop command, a repository deleted
by hand. And a kept ref is as safe as the disk the main repository is on, and a snapshot as safe as the
disk the state root is on. This rule is not a backup.

What a process of the owner's account removes outside Veldo is stopped only in part. An agent that
runs outside the sandbox can delete the snapshot store, or delete a kept ref and run git's garbage
collection; the protect list and the boundary check bind only Veldo's own code. The guard hook refuses
the shell command an agent types when it names the store or the kept refs (0.3, VELDO-0349). It does
not see a program the agent writes and runs, or a command that reaches them without naming them. For
those there is detection: the loss is reported at the next reconcile, at the next veldo space kept and
at any restore of that item, and never passed over (0.3, 0.5).

A clean clone whose remote is on another host is judged by its remote-tracking refs alone. A ref says
what that remote had at the last fetch, and it can be written by hand, so a commit the remote has
since lost, or never had, goes with the scratch folder the clone is in. Reading the remote would need
the network at every removal, and the design does not do that.

A worktree under its marked name can still be written by a process that finds that name. The move
before a Discard's or a Save's remove (0.3) closes the gap for every process that uses the
worktree's path, and the second in-use probe sees one that sits in the folder or holds a file of it.
A process that lists the parent folder, opens the marked name and writes there between that look
and git's remove is not seen. No run is given the marked name.

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
| Kind | What an item is: worktree, branch, agent repository, build output, scratch, evidence, container, volume, network, image tag. Every private repository is an item of the kind agent repository |
| Agent repository | The private git repository the sandbox makes for one agent. The agent's worktree belongs to it, and its commits reach the shared repository only when the runner brings them across. As a kind it also holds the worker clone, the batch clone and the candidate workspace, told apart by the item's form (4.1, section 5) |
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
| Protect list | Paths, Docker object names and compose project names that are never recorded, adopted, proposed or removed (section 7). The snapshot store is always on it (0.3) |
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
| Work | What section 0 protects: commits no kept ref holds, uncommitted and untracked changes, stashes, unpushed branches, evidence, and anything the owner marked Keep (0.1) |
| Main repository | The repository a worktree is linked to; for a private repository, and for an agent's worktree, the shared repository the declarations name. Never a private repository (section 0) |
| Private repository | A git repository made for one run: an agent repository, a worker clone, a batch clone or a candidate workspace |
| Kept ref | A ref under refs/veldo/kept/ in a main repository. Veldo writes it before a removal and never deletes it (0.2) |
| Keep step | The write of an item's kept refs and of its keep record, after rule 6 and before the tool of rule 7 (0.2) |
| Snapshot | The uncommitted state of a worktree, or of a worker clone's work tree, saved as plain files with a manifest in the snapshot store. Each attempt has a numbered folder of its own (0.3) |
| Snapshot store | The folder space-saved under the state root. It is outside every repository, and only the owner's drop command removes anything from it. Reconcile and veldo space kept check it against the keep records (0.3) |

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
| Ledger | engine/.veldo/control_space.py | New | Owns the item, pool, hold, reconcile, event, mode, wrong-proposal, review group and proof records in the control store. The only writer of them. Registers its commands and declares ownership of its entity kinds with the store's declare_owners, as control_andon.py:259 does |
| Declarations reader | engine/.veldo/control_space_config.py | New | Reads the installation's space section through the one installation reader, and each project's space file. Refuses a malformed one by name |
| Kind registry | engine/.veldo/control_space_kinds.py | New | Plain data and one pure function. For each kind: how an item is identified, its lifecycle table, which safety rules apply, which remover carries out each action |
| Probes | engine/.veldo/control_space_probe.py | New | The observers the safety rules read: process working directories, open and mapped files, container mounts, git state of a worktree and a branch, the protect list. Each returns facts; none decides. For the processes it cannot read it connects to the reader's socket, checks who wrote the answer and matches the numbers (7.1). Its entry reader-exec is what the reader's unit runs: it checks the installed binary and executes it |
| Process reader | engine/scripts/veldo_procread.c, added to the protected paths; installed by the owner at /usr/local/lib/veldo/veldo-procread | New | A static C program with the one file capability cap_sys_ptrace. Prints, for every process and every thread of it, the device and inode numbers of its working directory, open files and mapped files. Takes no input, attaches to nothing, signals nothing, writes nothing (7.1) |
| Reader units | engine/.veldo/services/veldo-procread.socket and veldo-procread@.service, added to the protected paths; installed by the owner into the systemd user unit folder, without sudo | New | A socket in the owner's runtime folder and the unit it starts, one instance per read. The unit sets no NoNewPrivileges, so the reader gets its capability there and nowhere in the service. The authority unit is not changed (7.1) |
| Removers | engine/.veldo/control_space_remove.py | New | One remover per action. Each uses the owning tool's own remove and reports what it measured |
| Keeper | engine/.veldo/control_space_keep.py | New | The keep step and the snapshot of section 0: writes an item's kept refs in its main repository, reads them back, hands the Ledger the keep record, and writes the saved snapshot to the snapshot store without touching the worktree or any object store. Also the reads behind kept and restore |
| Guard hook | engine/scripts/veldo-guard.sh, with its copies scripts/veldo-guard.sh and packs/claude/scripts/veldo-guard.sh. The first two are protected paths already | Changed | Gains one rule: it refuses an agent's shell command that names the snapshot store or refs/veldo/kept, and lets veldo space kept drop through (0.3, VELDO-0349) |
| Signal | engine/.veldo/control_space_signal.py | New | The one entry point an emitting process calls with an event. Finds due items, runs rules and removers in line, writes the outcomes |
| Docker adapter | engine/.veldo/control_space_docker.py | New | Per engine context: the run label and compose project name, the snapshot, the event subscription, the census, the object removers |
| Reconciler | engine/.veldo/control_space_reconcile.py | New | Snapshot of roots and engines, comparison with the ledger, adoption rules, the report. Also the check of every keep record against the kept refs and the snapshot store (0.3) |
| Admission | engine/.veldo/control_space_admission.py | New | Pools, needs, holds, the mark that says a waiting hold may be judged again, the no-space classification |
| Event spool | engine/.veldo/control_space_spool.py | New | Keeps an event that a hook or the CLI could not deliver because the authority was not reachable, and replays it in order |
| Event consumer | engine/.veldo/control_space_consumer.py, called from the authority service | New | Takes the oldest event record a hook left and hands it to the space worker. It runs no git command and computes nothing |
| Space worker | engine/.veldo/control_space_worker.py | New | The child process the service starts for one event record. It works out what the event ends (for a landing, which recorded branches the new commit contains), then runs Signal. Its output pipe is in the service loop's poll set |
| Clone provisioner | engine/.veldo/control_clone.py | Changed | Declares the clone root, work tree and scratch folder before making them: the work tree as an agent repository item with the form worker clone, the other two as scratch. Teardown and failed-provision cleanup go through Signal |
| Fleet worktrees | engine/.veldo/fleet.py | Changed | Declares the worktree before git adds it; removal goes through Signal, without git's force option |
| Batch | engine/.veldo/control_batch.py | Changed | Declares the batch clone, as an agent repository item with the form batch clone, and the observation folder, as evidence (lead decision of 2026-11-15, section 13), before making them (:530, :721); discard goes through Signal (:944-951) |
| Sandbox | engine/scripts/agent_sandbox.py, prepare, integrate and the launcher's scratch (protected, policy.yaml:22 and 35) | Changed | Declares the agent repository, the worktree and the branch before making them; integrate reports what it brought across. Under a recorded run it declares its scratch and leaves the removal to the run's event. Its pass that removed stale scratch by age is deleted |
| Gate leg timing | engine/scripts/gate_legs.py, prune_times (protected, policy.yaml:54-55) | Changed | Loses the branch that deletes a leg-time file for being older than 30 days. The 30-day value stays for the one reader that ignores an old measurement (6.10) |
| Settlement journey | engine/.veldo/control_request_settlement.py | Changed | Gains one request touchpoint, space disposition, whose three offered answers are picks. The set of rulings does not change (section 7) |
| Receiver | engine/.veldo/control_launch.py | Changed | Declares run folders (the run directory, artifacts, receipts, token records); sets the run's label and space environment; runs the census and sends run finished; classifies a no-space end. Its two direct removals of run directories go through Signal |
| Landing line | engine/.veldo/lander.py, control_launch_work.py | Changed | Candidate workspaces are declared as agent repository items with the form candidate workspace, never as scratch, and removed through Signal after the keep step |
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
| CLI | engine/bin/veldo | Changed | The verb space with status, reconcile, record, event, admit, run, covers, gate-check, reject, mode, kept, restore and prove |
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
| kind | One of the twelve kinds: the ten of the table in section 5, and review run scratch and review run build output (amended 2026-11-16, the lead's decision at assembly; the notes under that table) |
| form | For an agent repository item: which private repository it is. One of agent, worker clone, batch clone, candidate workspace. The creator states it at declare and reconcile at adopt. An item with no form is read as agent, the form that ends on the fewest events |
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
| kept | For a worktree and a private repository: the keep record. The main repository, each kept ref with its commit, the list of snapshot attempts, each with its path, its number, its size and its manifest digest, and the path the item had. Written before the remover runs (0.2). A later write adds refs and attempts and removes none (0.3), and the journal holds each version |
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
removed to the end, because the decision to remove it was already made and recorded. For a worktree
and a private repository that holds only with the keep record: reconcile completes one whose keep
record exists and whose every kept ref resolves, and defers any other as keep_failed (0.2).

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

### 4.10 Proof record

Identity: space:proved: followed by the host and a new identifier. One record each time the owner runs
veldo space prove (0.7). Only the owner's signed command writes it; no host principal may.

| Field | Content |
| :- | :- |
| host | The host the suite ran on |
| modules | The SHA-256 digest over the space modules as installed, file by file in name order |
| git | The version of the git the suite ran with |
| result | passed or failed, with the number of rows and the name of each row that failed |
| day | The calendar day of the run, in the installation's time zone |

The record is read, never counted down. The mode command and Signal compare its two digests with the
modules and the git in use at that moment.

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
| Agent repository whose form is a worker clone, a batch clone or a candidate workspace | Remove as an agent repository is removed: the keep step, then the folder remover, once rule 5 finds no unique work in it; otherwise deferred as unique work. A worker clone of a run that has ended is saved and removed (0.3) | The same | The same | The same | The same |
| Branch | | | Mark contained; keep | Keep | Keep |

Amended 2026-11-15 (the lead's decision, from the review of VELDO-0337, finding 1). An item's own
declared end events govern its removal, and where this table and that rule disagree the rule holds. A
review is not over when its receiver ends: the verdict is validated, signed and recorded after that, by
the one writer of the verdict. So a review run's scratch folder and build root are declared at creation
with their own end events, verdict recorded and the events after it, and without run finished. For
those two items the run finished cell of the scratch and build output rows does nothing: run finished
removes only an item whose own end events list run finished, and never an item that waits for a later
event. They go at verdict recorded, which the writer of the verdict sends after its commit
(VELDO-0337); a verdict recorded that was lost between the commit and the send is sent again at start,
from the committed verdict. A review that ends with no verdict sends run finished only, and its scratch
folder and build root then wait for their later events (ticket ended, project ended). Everything else
of a review run keeps its row: its run directory ends at
run finished, the build output the census declares inside its worktree goes at run finished before
the worktree, and its worktree is removed as the review worktree row says. The ledger holds the
declaration on the item (4.1, ends_on), so every sender of run finished is bound by it, not only the
receiver. In the table of events below, "the review's receiver" as the emitter of verdict recorded
reads "the writer of the review's verdict, after its commit" (the lead's decision of the same day,
VELDO-0337 History).

Amended 2026-11-16 (the lead's decision at assembly, as VELDO-0324 decided). Declare takes no end list:
an item's end events come from its kind in the kind registry alone (4.1, 6.1). The two items above are
therefore declared with kinds of their own, review run scratch and review run build output, removed by
the folder remover, whose end events are verdict recorded, ticket ended and project ended, and never run
finished.

Amended 2026-11-16 (the lead's decision, from the review of the assembly, finding 5). The wording
follows the two kinds. A review's scratch folder and build root end on verdict recorded, ticket ended
and project ended, and on no other event: the note of 2026-11-15 above said that with no verdict they
wait for "landed or contained, ticket ended, project ended, worktree abandoned", which was the end
list of the plain scratch and build output kinds less run finished, and it now names the two events
they do wait for. Landed, contained, worktree abandoned and released do nothing to them. There are
twelve kinds, the ten of the table above and these two, and 4.1 says so; "the ten kinds stay" in the
revision table of 0.8 is what was true of VELDO-0298 at that revision.

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

Every Remove in this table stands under section 0. A worktree and a private repository go only after
the keep step has recorded their commits.

Which kind a private repository is. A worker clone, a batch clone and a candidate workspace are
declared, and adopted, as items of the kind agent repository, each with its form (4.1). They are never
declared or adopted as scratch, whatever their creator once called them. There is no eleventh kind:
every rule, probe, look and remover that names the agent repository kind then holds for all four
without being told, and the kind is what picks the remover. The form picks the row. The sandbox's own
agent repository keeps the first of the two rows. The other three take the second: they end at the
events their creators already send for them (run finished for a worker clone's teardown and for a
batch's discard, and the event the landing line sends at its close), where the first row does nothing
at run finished. An
item with no form takes the first row, so a creator that forgets the form leaves a clone in place
longer and never removes it sooner.

How they are removed is the same for all four: rules 1 to 6, with rule 5 comparing the repository with
its main repository, then the keep step, then the folder remover (6.5). One difference, by the lead's
answer: a worker clone whose run has ended is not deferred for uncommitted files. They are saved in
the snapshot store and the clone is removed (0.3). A worker clone is known by its form and by its
manifest under the state root, which names the dispatch that owns the item; a private repository that
cannot be shown to be one waits for the owner as an agent repository does.

What a clone's creator declares beside it stays scratch, because it is no repository: a worker clone's
root and its scratch folder. The root holds the work tree, so it waits for it as any parent waits for a
child. A batch's observation folder is not scratch: it is evidence the reviewer reads (lead decision of
2026-11-15, section 13).

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
| declare | kind, host, locator, owner, creator, parent, start, and for an agent repository its form | Creates an item in state declared, with pool and ends_on filled in | A locator on the protect list; a locator outside every known root; a second live item with the same locator; a form on an item of another kind |
| confirm | item | declared to present | An item not in state declared |
| measure | item, bytes, event | Writes size | |
| signal | event, subject | Marks every present, kept or deferred item whose owner matches the subject and whose table has an action at this event as due; returns them in removal order | An unknown event |
| outcome | item, one of removed, deferred, kept, with the facts | Writes the state and the removal or deferral fields | An item not due or removing; removed for a worktree or a private repository that has no keep record |
| adopt | what reconcile found, the rule that proved the owner | Creates an item in state present with adopted true | The same refusals as declare |
| report | what reconcile found, and a proposed owner when a rule gives one | Creates or refreshes a report record; never an owner | |
| gone | item | present, declared, due or deferred to gone | |
| rebranch | worktree item, new branch, new start commit | Writes the item's branch and start; declares a branch item for the new branch when it has none | An item that is not a worktree, or is not present, kept or deferred |
| keep | a worktree or a private repository item that is due, its main repository, each kept ref with its commit, the snapshot's path with its attempt number, its size and its manifest digest when there is one | Writes the keep record on the item (4.1). For an item that already has one it adds the refs and the snapshot attempt to the record. Nothing this command is given replaces or removes a ref or an attempt the record holds | An item that is not due or removing; a main repository that is a private repository; a ref that does not resolve to the commit named, a snapshot path that is not a numbered folder of that item in the snapshot store, or a manifest that does not have the digest named, each read by the Ledger itself |
| proved | host, modules digest, git version, result | Writes a proof record (4.10) | A command not signed by the owner |
| restore | a removed item, and optionally a path and one of its kept refs | Adds a worktree at the kept commit and applies every snapshot attempt the keep record lists, the oldest first (0.5). Removes nothing | A command not signed by the owner; a path where something exists; an item with no keep record; a kept ref that does not resolve to its commit; any snapshot attempt the record lists whose folder or manifest is missing, whose manifest has another digest, or one of whose files does not match the manifest; a manifest path that leads outside the target |
| drop kept | a removed item | Deletes that item's kept refs and its whole folder in the snapshot store, every attempt in it, and marks the keep record dropped (0.5) | A command not signed by the owner |
| event | type, subject, emitter | Creates an event record in state received | An unknown type; a ref changed event for a repository that is neither bound nor plain; a released event that names an item a Veldo seam declared, or no item |
| consumed | event record, result | received to consumed | A record already consumed |
| reject | an item that is due, an adopted item, or a report with a proposed owner; the owner's reason | Writes a wrong-proposal record and applies its effect (4.8) | A command not signed by the owner; a subject that is none of the three |
| confirm group | scope, kind | Writes confirmed on every due item of that group the owner has not marked wrong, and hands the group to the space worker, which runs Signal for it | A command not signed by the owner; a scope in act mode |
| mode | scope, new mode | Writes the mode record and its history | A command not signed by the owner. For a switch to act: a scope whose last three calendar days were not each a clean report day, or with a wrong-proposal record dated today; a scope with an unconfirmed pending group; a bound project whose gate script lacks a space step; no proof record that passed for the space modules and the git in use (0.7). The refusal names the day that failed and why, each open group by scope and kind with its count, and each missing gate call |
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

Four git commands are removal primitives too, since section 0: a ref delete, a stash drop or clear, a
reflog expire and a prune of objects. The check refuses each one anywhere but in the owner's kept drop
command, so no later change can quietly delete a kept ref or the commits behind it.

2026-11-15 lead decision (VELDO-0304): the pin, staging and scaffold ref releases call the
central ref remover. With a ledger it requires the owner's ended item and event and verifies its keep record;
and proves that a kept ref or branch in the main repository reaches the commit before a non-forced,
value-checked deletion of the temporary ref. Without a ledger, the standalone look and keep result
provides authority instead. A missing ledger alone never refuses removal. Without the keep and
reachability proof the ref stays. This grants no direct
ref deletion to the three callers, and no stash, reflog or object pruning to the ref remover.

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

1. In the run's worktree, ask git for untracked paths, ignored ones included, and for the rule that
   ignores each. An ignored folder at any depth that git reports as a whole is a build output item,
   whatever its name, when a committed ignore file of the project or a declared pattern covers it.
   Untracked paths that git does not ignore are unique work: they are not recorded as items, and they
   protect the worktree (section 7). Since section 0 the same holds for an ignored folder that only a
   personal ignore rule covers, for a loose ignored file outside every build output folder, and for a
   path whose rule cannot be traced.
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
| Remove a disk folder | Rename it to a marked name beside itself, run the in-use probe again on the new name, then delete it; if the second probe finds a user, rename it back and defer. Where the removal compares each file with a manifest and that comparison stops it, rename what is left back as well, before the item is deferred (0.3). The marked name holds the item's id, so reconcile finds a folder left under it. Before the delete it opens up directories a confined process left unreadable or unwritable, through descriptors and without following a link, as the sandbox's own remove_tree does today (agent_sandbox.py:2052-2071) | The folder is a mount point, or is not on the item's pool |
| Remove a worktree | The keep step (0.2), then git's worktree remove, without the force option. For an agent's worktree the kept refs are fetched into the shared repository and written there. After a Save, the worktree is first moved to a marked name beside itself by git's worktree move, and the remove runs only while, under that name, it is not in use and its ignored files that are work equal the snapshot (0.3) | A kept ref could not be written or read back; the main repository is not at its path; git finds a modified tracked file or an untracked file; after a Save, git refuses the move, the worktree is in use under its marked name, or an ignored file that is work is new or changed |
| Remove an agent repository, or any other private repository | The keep step (0.2), which brings every ref, stash entry and log commit across to the main repository, then the folder remover, after the unique work rule has compared its branches with the shared repository. For a worker clone whose run has ended, the snapshot of its uncommitted state is written between the two (0.3), and the folder remover compares each file of the work tree that is work with the manifest immediately before it deletes it. A stop by that comparison renames the folder back to its locator | A kept ref could not be written or read back; no main repository is named, or it is not at its path; the snapshot could not be written, synced, read back or renamed into place; a file is not in the manifest or differs from it |
| Remove an image tag | The engine's image remove, without the force option, on the tag | A container uses the image |
| Stop and remove a container | The engine's stop, then remove, without the force option | |
| Remove a volume | The engine's volume remove | A container uses the volume |
| Remove a network | The engine's network remove | An endpoint is attached |
| Drop caches in an evidence folder | Remove the sub-folders the project declares as caches; nothing else | |
| Mark a branch contained | A ledger write; git is not called | |
| Remove review scratch | For a review worktree only. Asks git for the worktree's untracked paths that it does not ignore and removes each one: a folder by the folder remover's rename, second probe and delete, a file by a plain delete, a link by deleting the link and never what it points at. Each path passes rules 1, 2, 3, 4 and 6 first, and the snapshot of all of them is in the snapshot store, with its keep record written, before the first is deleted (0.3). Immediately before each file is deleted, its mode and digest are compared with the manifest; for a folder that is done for each file in it. No force option and no clean command of git is used | A path resolves outside the worktree, is on the protect list, or is in use; the snapshot could not be written, synced, read back or renamed into place; a file is not in the manifest or differs from it |
| Discard a worktree | git's worktree remove with the force option, on a worktree named by a settled owner decision: the one worktree of its request, each worktree of a review group, or the one member a member pick names. First the keep step and the snapshot of the uncommitted state (0.2, 0.3), and both are compared with the terms the owner was shown. Then, for a detached worktree whose checked-out commit no ref holds, a kept branch is created at that commit in the shared repository, read back, and recorded by the Ledger. The remove runs only after all three. Before the remove the worktree is moved to a marked name beside itself by git's worktree move, without the force option, the in-use probe and the comparison with the snapshot are made again under that name, and a user or a difference moves it back to its path | The decision is not settled, does not name that worktree, the worktree's list of changed files differs from the list the owner was shown, the kept branch could not be created, a kept ref could not be written, the snapshot could not be written, synced, read back or renamed into place, the worktree no longer equals the snapshot, git refuses the move to the marked name, or the worktree is in use under that name |

No remover calls a prune command. No remover passes a force option, with the one exception in the last
row. Discard is the one forced removal, and it is allowed only after the owner's discard answer (section
7). Discard removes the worktree and never the branch, so work that was committed on a branch survives
it.

Discard never loses a commit (the lead's decision (g)). A detached worktree has no branch, so a commit
made in it can be reachable from no ref (rule 5, case 5). On such a worktree the settled Discard first
runs the keep step and the snapshot and compares both with the terms the owner was shown, so the
checked-out commit is the one the owner saw, and a Discard refused for changed terms writes no ref.
Then, before the worktree is moved or removed, the discard remover creates a kept branch at that commit
and reads it back, and the Ledger, which reads the branch and the worktree's HEAD itself, records it as
a branch item in state kept. The branch is named as Save names one: the ticket's kept-branch name for a
ticket's worktree, otherwise the prefix space-saved, then the run's label. Every character of the label
that git refuses in a ref name is replaced by '-', and git checks the name before the write. Only then is
the worktree removed with the force option. What Discard removes from disk is uncommitted work only:
tracked edits, staged changes and untracked files. Since section 0 it saves them first, as a snapshot
in the snapshot store, so it loses nothing (0.3).

For this test only a branch holds a commit, because no branch is ever deleted. A tag can be moved or
deleted and a remote-tracking ref goes with a prune (section 0), so a commit that only one of them
reaches gets a kept branch like any other. A kept name is taken when a branch holding other work has
it, when another open request has named it, and when the branch item at it is due, deferred or
removing, since no kept branch is recorded onto an item that is on its way out; the next name is used.

The order has one failure. When the branch cannot be created, because the name is taken by a branch
that does not hold the commit or because git refuses the ref, the discard does not run and the worktree
is deferred as remove_refused with everything in it. Discard never proceeds without the branch.

The commit has a ref at every point where the process can stop. Before the branch it is on the kept ref
the keep step wrote, and the worktree is untouched. Between the branch and its record it is on both,
and reconcile, as it defers the removing worktree at the next start, finds the branch at the commit
under the name the terms showed and records it, so an owner's Keep that follows leaves no unrecorded
branch. The next Discard of that worktree finds the same branch under the same name: one branch, one
item, never a second name. After the record it is on the recorded branch.

Creating the branch is a ref write. It is not a removal, so Discard stays the one forced removal. It is
not a commit, so "Veldo never commits on its own" still holds. git runs the reference-transaction hook
for it, and the hook sends nothing, because the ref is neither the trunk nor a declared landing ref
(6.9).

An agent's worktree on its branch needs no new branch. Its commits are on its branch in the agent
repository, which rule 5 keeps until the runner's integrate has brought them across. A detached worktree
of an agent repository whose commit no ref holds gets its kept branch in the shared repository, where
the keep step has already put the commit on a kept ref, and never in the agent repository, which is
private and goes later (0.2). When the shared repository cannot take the branch the discard does not
run. Discard of an agent's worktree
removes the worktree and leaves the agent repository and its branch in place, kept. The worktree's
kept refs are in the shared repository by then (0.2), so they are still there after the agent
repository has gone too.

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
| space.kept | For each removed worktree and private repository: its ticket, the path it had, the event, each kept ref with its commit and whether it still resolves, each snapshot attempt its keep record lists with its number and size and whether it is still there and whole, and the restore command (0.5). For the installation: the count and the size of all kept refs and of all snapshots. The size of the kept refs is that of the objects only they reach, measured at reconcile |
| space.reports | What reconcile found and could not adopt, with the proposed owner when a rule gives one; repositories whose hooks are missing; bound projects whose gate script lacks the space steps. Kept work missing: each kept ref that does not resolve to its recorded commit and each snapshot that is missing or not whole, with the item, and a snapshot store that is gone or has another owner or mode (0.3). Snapshot folders no keep record names, with their sizes, as information |
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
| space.restore | Brings a removed worktree back from its kept refs and its saved snapshot (0.5) |
| space.kept.drop | Deletes one removed item's kept refs and its snapshot, after listing the commits that would no longer be reachable and the snapshot's files |

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
| process reader | The word none, or the SHA-256 digest of the process reader: the one the gate recorded for the reviewed source and the owner installed (7.1). The reader's path and its socket's path are fixed in the probe and are not keys |
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
| build output | Extra folder and file name patterns, for adopted worktrees, for folders git does not ignore, and for loose ignored files a tool makes again (0.1) | None |
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
| control_clone.py:757-761 | Deletes the clone's work tree, scratch and root, ignoring errors, after the clone_in_use check | The clone_in_use refusal stays first, unchanged. Then Signal with run finished for the clone's items. The work tree is an agent repository item with the form worker clone: the rules, the keep step, the snapshot when its run has ended with uncommitted files, then the folder remover. The scratch folder and the root are scratch and go through the folder remover, the root after the work tree. The pins are released only after the removal outcome is written |
| control_clone.py:606 | Deletes the clone root when provisioning fails | The declared items go the same way as at teardown: the work tree, when it already holds a repository, through the keep step and then the folder remover, the rest through the folder remover. They are then marked gone |
| control_launch.py:762-787, clear_runs, called from Runner.sweep at :714-722 | Deletes the run directory of each leftover dispatch whose run the kernel shows gone | The run directory (under runs_root, control_launch.py:538-542) is a scratch item owned by its dispatch. clear_runs calls Signal with run finished for the leftover; its kernel test is rule 3 |
| control_launch.py:1389-1397, _remove_run | The receiver deletes its run directory before it reports its end | The same item, removed by the receiver's Signal at run finished |
| control_launch_work.py:105-107 | Deletes the landing line's candidate folders at close | A candidate folder is an agent repository item with the form candidate workspace, never scratch. It is removed through Signal at close: the rules, the keep step, then the folder remover |
| lander.py:534-541, discard | Deletes the candidate workspace and observation folder | The candidate workspace the same way. The observation folder holds no repository and is scratch |
| control_batch.py:944-951, discard | Deletes the batch clone (made at :530 under the workspace root) and its observation folder (made at :721), ignoring errors | Both are declared before they are made, owned by the batch's project and gate: the clone as an agent repository item with the form batch clone and its main repository, the observation folder as evidence (lead decision of 2026-11-15, section 13). discard calls Signal with run finished for the batch's items. The clone goes through the rules, the keep step and then the folder remover. The observation folder is kept at run finished and follows the evidence row of the kind registry: its caches are dropped at verdict recorded, and it is removed at ticket ended or project ended, whichever comes first; a refusal is a deferral, not an ignored error |
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

2026-11-15 lead decision (VELDO-0304): the reviewed class also includes a process removing a
temporary tree it created itself (mkdtemp, system temporary directory, its own prefix, refusing
anything else). The protected scripts/check_first_use.py function _rmtree is one such site and
stays unchanged. A scoped TemporaryDirectory is the same class only when it has an explicit
prefix, uses the system temporary directory and cleans only its exact mkdtemp result. A custom
root or an extra recursive delete does not get that exception. The following functions are named
with that reason; engine entries also name their installed copies.

| Path | Function | Reason |
| :- | :- | :- |
| engine/.veldo/action_executor.py | _cli | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/authority_contract.py | ssh_keygen_verify | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_agent_config_handoff.py | codex_observe | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_api_webauthn.py | openssl_verifies | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_architecture.py | ArchitectureAuthority._judge | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_batch.py | Batch._merge | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_engine_codex.py | bundled_catalog | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_engine_codex.py | feature_listing | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_factory_setup_dispatch.py | checked_work | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_graph_isolation.py | probe_graph | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_graph_isolation.py | run_entry | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_launch_work.py | Runtime._collect | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_memory_check.py | probe | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_runtime.py | metadata_problems | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_runtime.py | probe_graph | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_runtime.py | qualify | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_runtime.py | run_hidden | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_service.py | find_principals | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_space_probe.py | reader_check | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_workflow_cycle.py | Cycles._exchange | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/control_workflow_cycle_pm.py | ProjectCycles.exchange | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/executor.py | LiveLoop.gate | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/git_process.py | _invoke | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/lander.py | GitLandOps._union_resolve_one | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/pack_conformance.py | _conform_one | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/pack_conformance.py | gate_exit_for_state | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/pack_conformance.py | real_push_exec_bit | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/qualify.py | claude_builtins | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/.veldo/qualify.py | fixtures | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| engine/scripts/check_gate_mutations.py | run_stage | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/check_first_use.py | _rmtree | Lead decision 2026-11-15: only its own mkdtemp tree, system temporary directory and own prefix. |
| scripts/check_install_and_run.py | check | Lead decision class: only the mkdtemp result created by this call, with its own prefix. |
| scripts/check_review_mutations.py | main | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/drive.py | main | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/drive.py | red | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/parser_corpus_audit.py | main | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/propose_case_inputs.py | trace_case | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/render_pdfs.py | main | Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree. |
| scripts/suite_equiv.py | main | Lead decision class: only each mkdtemp result this call created with its own prefix. |

The list also names engine/scripts/gate_schedule.py:Meter.finish and
engine/scripts/mutation_ownership.py:WorkerMeter.close, with their installed copies. Each removes
only its ended worker's empty kernel cgroup directories with rmdir, which cannot remove ordinary files.
The hand-rolled traversal check counts these as folder removal, so their reasons are explicit.

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
| The owner | Console and CLI | Adopt, Abandon, Confirm, Reconcile, marking a proposal wrong, the mode switch, changes to the protect list, the answers to a decision request, restore, kept drop and the proof record | |

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

The keep step (section 0.2). It is not an eighth rule, and the rules keep their numbers. When rules 1
to 6 have passed for a worktree or a private repository, the remover first records every commit the
item reaches on kept refs in its main repository, reads them back and has the Ledger write the keep
record. Only then does it call the tool of rule 7. A failure is the deferral keep_failed, and nothing
is removed. For an agent's worktree the main repository is the shared repository, never the agent
repository (0.2). Where the removal also saves a snapshot, that save is part of the step, and it fails
the same way (0.3).

Rule 5, unique work. For a worktree it refuses in any of these cases:

1. a tracked file is modified;
2. a change is staged;
3. an untracked file exists that git does not ignore, or an ignored one that is not build output
   (section 0.1);
4. an operation is in progress (a merge, a rebase, a cherry-pick);
5. a commit on the worktree's branch is reachable from no ref other than that branch itself, from no
   completed landing's source commit and not from the trunk. The test covers every commit on the branch.
   The branch tip is the checked-out commit, so testing the tip against the other refs is enough, but the
   rule is about the branch and not about what happens to be checked out. A detached worktree is tested
   on its checked-out commit against every ref. A ref here is a branch, a tag or a remote-tracking ref.
   A stash is not one: the stash entry made in a worktree has the checked-out commit as its parent, so
   git lists refs/stash among the refs that reach it, and once the worktree is removed and the stash
   dropped the commit is lost. Git's per-worktree refs do not count either, and neither does a kept
   ref: it is there so that nothing is lost, and it is never a reason to remove.

Case 3 has one exception, by name: review scratch. In a review worktree an untracked file that git does
not ignore is not unique work (below). And it has one reading that belongs to Save alone: at the
remove that follows a settled Save, an ignored file that is work does not refuse when it is in the
snapshot the keep record names with the same mode and digest. Any other ignored file that is work
refuses there as everywhere (0.3).

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
  kernel's process table, for every thread of the process (7.1, "Every thread"): a thread can have a
  working directory and a descriptor table of its own, and the entries directly under /proc/<pid> show
  the first thread's only. A command line that mentions the path is not use: that test also matches the
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
- A Discard's and a Save's move of the worktree to a marked name closes the same gap between the last
  look at the worktree and git's remove (0.3, 6.5).
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
the reader is a program of its own, in a unit of its own beside the service, and it exits when it has
printed. Without the reader, or with one that is not the binary the owner installed, unread processes
are judged by the bound above as before, and the probe says so.

This is the section's second revision, after its validation
(design-veldo-0344-validation-2026-11-14.md, verdict CHANGES; 14.6). The validation accepted the
shape and the one capability. It changed five things: where the reader runs, that every thread is
read, how the binary is built and pinned, how numbers are matched, and what the seccomp filter is said
to do.

A second validation (design-veldo-nowork-0344r2-validation-2026-11-14.md; 14.7) found all seven
points resolved and kept the writer check this revision had added. It closed two holes in that check,
and one in the install line: the writer is now held by a pidfd, the reader waits for the probe before
it exits, and the source is read past git's replace refs.

The final check (design-veldo-nowork-r2-validation-2026-11-14.md; 14.8) found one more hole in the
writer check: a process that writes first and then executes the reader in its own place. The reader
now locks itself before it writes its header, and it writes the table only after the probe has sent
it one byte.

What one capability reads. Measured on this host on 2026-11-13 (kernel 7.0), against a process the
probe cannot read today:

| Entry of /proc/<pid> | Without the capability | With cap_sys_ptrace alone | What it gives |
| :- | :- | :- | :- |
| cwd, by stat through the link | Refused | Read | The device and inode number of the working directory |
| maps | Refused | Read | The device and inode number of every mapped file |
| fdinfo/<n> | Refused | Read | The mount id and the inode number of every open descriptor |
| mountinfo | Read | Read | The device of every mount id |
| fd, the folder of links | Refused | Refused | The paths of the open files |
| task/<tid>/cwd and task/<tid>/fdinfo/<n> | Refused | Not measured | The same two facts for one thread |

The fd row changes one word of the decision. The decision lists fd among what the reader reads. The
fd folder is mode 0500 and belongs to the process's uid, or to root when the process is not dumpable.
Listing it is an ordinary permission check, and cap_sys_ptrace does not pass it; it took
cap_dac_read_search as well before the folder could be listed. So the reader reads fdinfo in its place
and stays at one capability. The validation measured the same from the other side and accepted it: a
second capability would let the reader, or a mistake in it, read every file on the host, and would buy
only paths. The lead confirmed one capability.

The measurement ran in a container that shares the host's process table, as uid 0 holding
cap_sys_ptrace and nothing else, against a process of the owner's. The installed reader runs as the
owner against entries that belong to root, which is the same check from the other side. The task
entries were not read with the capability: the task folder is mode 0555 and its entries take the same
check as the ones above. A row that runs where the reader is installed proves both on the host
(VELDO-0344 AC6).

Every thread. The entries directly under /proc/<pid> are the first thread's. A thread that left the
shared file system state has a working directory of its own, and one that left the shared descriptor
table has open files of its own. The validation measured it on this host: a process whose first thread
sat outside a folder and whose second thread had moved into it showed the outside folder at
/proc/<pid>/cwd and the inside one only at /proc/<pid>/task/<tid>/cwd. A reader of the first thread
alone would call that folder free, and removing it would take a working directory from under a live
thread. So the reader reads the working directory and every fdinfo entry of every task. Mapped files
belong to the process's one memory map and are read once. On this host that is 2,767 tasks in 786
processes. The probe's own reading of the processes it may read had the same gap, and VELDO-0344
closes it there too (AC8).

Numbers, not paths. The reader prints device and inode numbers for all three facts and never a path.
There are three reasons. One capability gives no path for an open descriptor. A path is also the wrong
thing to compare: a process in a container or in a sandbox has its own mounts, and the path the kernel
prints for its working directory is not a host path, while the inode number is the same in every mount
namespace. And numbers disclose less to whoever runs the reader (below).

Where the reader runs. The kernel grants a file capability when a program is executed, and it grants
none to a process that has no_new_privs set. The authority unit sets NoNewPrivileges=yes
(engine/.veldo/services/veldo-authority.service, line 17), every child inherits it, and the space
worker is a child of the service. The first form of this section had the probe start the reader. In
the service that reader would have held nothing and said cap=0, while the owner's check from a login
shell said cap=1. The validation found this.

So the reader runs in a systemd user unit of its own, beside the authority unit, started by a socket
(the lead's decision). It is a user unit: the owner installs it without sudo, and the owner's user
manager runs it under the owner's uid. It is not a system service and there is no second account. The
authority unit is not changed. It keeps NoNewPrivileges=yes, and neither the service nor any child of
it ever holds the capability.

Two unit files, templates under engine/.veldo/services beside the authority's:

```
# veldo-procread.socket
[Socket]
ListenStream=%t/veldo-procread.sock
SocketMode=0600
Accept=yes
MaxConnections=4

[Install]
WantedBy=sockets.target
```

```
# veldo-procread@.service
[Service]
ExecStart=@PYTHON@ -I -B @EXECUTABLE@ reader-exec
StandardInput=null
StandardOutput=socket
StandardError=null
RuntimeMaxSec=60
```

The service unit has no NoNewPrivileges line and none of systemd's sandboxing settings, because a user
manager applies some of those by setting no_new_privs. The reader shuts itself in after it has been
executed (below). RuntimeMaxSec ends a reader that hangs, and one whose probe never closes the
connection; its output is then cut and refused. It removes nothing and decides nothing.

Measured on this host on 2026-11-13 (systemd 255) with transient user units: a plain one runs with
NoNewPrivs 0 and the full capability bounding set. With NoNewPrivileges=yes it runs with NoNewPrivs 1,
and so it does with SystemCallArchitectures=native and no NoNewPrivileges line. Not measured: the two
unit files as written above, because a transient unit does not take Accept=yes, and the capability
arriving inside the unit, which needs the installed binary. The installed row proves both (AC6).

Each connection starts one instance. Its command is the probe's own entry reader-exec, from the
authority checkout. That entry opens the reader at its fixed path once, makes checks 2 to 4 below on
the open descriptor, and executes that same descriptor, with an empty environment and the connection
as standard output. So the file that was checked is the file that runs, also when root installs
another one in between. When a check fails it executes nothing and closes the connection.

Every probe reads through the socket, whoever runs it: the space worker, a receiver, a gate, the run
wrapper and the owner's own check. No probe executes the reader itself. The socket's path is fixed in
the probe as /run/user/<uid>/veldo-procread.sock. A probe that cannot reach it, such as one inside the
sandbox, reports the reader as refused and judges by the bound.

Who is on the other end. A socket in the owner's runtime folder can be taken over by any process of
the owner's. An agent outside the sandbox could stop the socket unit, listen at the path itself and
answer with an empty table. So the probe does not trust the socket. It trusts what the kernel says
about who wrote each byte. The probe sets SO_PASSCRED and SO_PASSPIDFD on its end before it connects,
and the kernel then attaches to everything the probe receives the writer's process id and uid, and a
pidfd: a descriptor that stands for that one process and for no later process that gets the same
number. The probe takes the output only when all of it was written by one process, and that process's
status file shows the owner's uid and exactly cap_sys_ptrace in its permitted and effective sets.

The pidfd is what ties the status file to the writer. A process id is a number the kernel hands out
again. Without the pidfd a stand-in could write a whole fake output and exit, a real reader started
through a second connection could land on the same number, and the probe would read the real reader's
status for the stand-in's bytes. So the probe reads the process id from the pidfd's own fdinfo entry
(the kernel writes -1 there once the process has ended), reads the status file and the start time of
that id, and then asks the pidfd again. The output is used only when the pidfd named a live process
before and after the status was read, and when it is the same process at the header and at the end
line. A writer that has ended, a part with no pidfd, or a kernel that does not know SO_PASSPIDFD
(before 6.5) refuses the output as refused:writer, and the bound judges.

A writer that becomes the reader. The writer has to be the locked reader at the moment it writes, and
not only at the moment the probe looks. Executing a program keeps the process: the same id, the same
pidfd, the same start time. The reader's unit files are in the owner's user unit folder, so any
process of the owner's can change the unit's start line to run a wrapper. The wrapper writes a whole
fake table to the connection, moves its standard output to a socket pair of its own, and executes the
installed reader. The reader gets its capability, writes its real table into the socket pair and
waits there. The probe then sees one writer, alive before and after, with the owner's uid and exactly
cap_sys_ptrace, and it would take the fake table. The final check found this. It follows from how the
kernel defines execve; it was not run on this host, and ticket 0344's row is where it is shown.

Two things close it. The first is a fact only the locked reader can show. The probe also requires
NoNewPrivs 1 and Seccomp 2 in the writer's status. A process holds cap_sys_ptrace and a seccomp filter
together only when it executed the installed binary first and filtered itself afterwards. A filter
installed before the execution needs no_new_privs, which stops the capability, or CAP_SYS_ADMIN, which
a process of the owner's does not have. The reader's filter refuses execve, so from that moment the
process cannot become another program.

The second is the order of the bytes. The reader writes only its header line once it is locked, and
then reads one byte on descriptor 1. The probe checks the header's writer, by the pidfd and by the
status with those two fields, and only then sends the byte. The reader writes the table after it has
read it. The probe refuses the output as refused:writer when anything but the one header line arrives
before it has sent its byte. So bytes written before the execution cannot be the table. The wrapper
gains nothing from the real reader either: a locked reader writes to its descriptor 1 and nowhere
else, and when that is the wrapper's socket pair, the connection gets nothing after the byte.

The reader stays until the probe has looked. Its whole output can fit in the socket's buffer: on this
host the table is 2,767 tasks. A reader that wrote and exited at once could be gone, and reaped by the
user manager, before the probe read its status, and the check above would then refuse a good output
now and then. So after its end line the reader makes one blocking read on descriptor 1 and exits when
that returns, which is when the probe has shut down its writing side or closed its end. The probe
does that only after its last look at the pidfd, and then reads to the end of the connection. The
reader sends nothing after the end line and uses nothing it reads there.

A process of the owner's with that capability can come only from executing the installed binary, which
checks 2 to 4 tie to the reviewed source. It takes no input, and nothing without the capability can
attach to it. A stand-in has no capability. A program that runs the real reader and passes its output
on writes under its own process id. A program that writes first and then becomes the reader is
stopped by the lock and the order of the bytes (above). Measured on this host on 2026-11-13: with SO_PASSCRED set, each
part received carried its writer's process id; a child's write and its parent's writes on one
connection arrived as separate parts with different ids; and the socket's peer credentials name the
user manager, which is why they are not used. Measured the same day for the pidfd (kernel 7.0, a
stream socket with SO_PASSPIDFD set before the connect): each part carried a pidfd of its writer; for
a writer that had written, exited and been reaped before the probe read, the pidfd's fdinfo gave -1
and the pidfd polled as ended, while the credentials still gave its old number; for a live writer the
fdinfo gave its process id. The first validation did not ask for this check. It is here because moving
the reader behind a socket would otherwise undo check 4: the digest of a file says nothing about who
answers on a socket. The second validation kept it and asked for the pidfd and for the reader's wait.

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
- Before it reads anything it sets no_new_privs and installs a seccomp filter. The filter is a list of
  what is allowed, for the native architecture only, with the x32 call numbers refused: openat with
  read-only flags (none of O_WRONLY, O_RDWR, O_CREAT and O_TRUNC), read, getdents64, the stat calls and
  fstatfs, close, memory for its own buffers, write to descriptor 1 and no other, and exit. Any other
  call ends the process. That includes every call the capability would make dangerous: ptrace,
  process_vm_readv, process_vm_writev, pidfd_open, pidfd_getfd, kcmp, kill, tkill, tgkill,
  rt_sigqueueinfo and pidfd_send_signal.
- What the filter enforces, and what it does not. The kernel, and not only the source, keeps the
  reader from attaching to a process, signalling one, writing to one, taking a descriptor from one or
  opening any file for writing. The kernel does not keep it to the entries named here. A seccomp filter
  cannot see the path of an open, so a program with this capability and this filter could still open
  another process's memory or environment for reading and print it. What keeps this reader from doing
  that is its source, which is reviewed, and the digest that ties the installed binary to that source.
- For every process in the table that is not a kernel thread it reads stat (the start time and the
  flags), mountinfo and maps, and for every task under its task folder the working directory by stat
  and every fdinfo entry. After the last task it lists the task folder again, and a task it has not
  read is an unread fact. A task that has ended when it is read holds nothing and gets no line. The
  reader opens nothing outside /proc.
- After the header line it makes one blocking read on descriptor 1, and it reads the process table
  only when that read has returned (above, "A writer that becomes the reader"). It goes on whatever
  the read returns, a byte, the end of the stream or an error, because the probe is the side that
  refuses a table sent too early. Run with a pipe or a file as standard output, the read returns at
  once.
- A write that fails ends the reader at once, with exit status 3 and no end line. A short write is
  continued until every byte is out. So a full or closed connection cannot drop a line from the middle
  of an output that still ends well.
- After the end line it makes one blocking read on descriptor 1 and exits when the read returns
  (above, "The reader stays until the probe has looked"). Run with a pipe or a file as standard
  output, the read fails at once and the reader exits the same way.
- Before the header it asks the kernel what /proc is, with fstatfs on the open folder. When the answer
  is not the process file system, it writes nothing and exits with status 4. A folder of ordinary
  files made to look like a process table is refused that way.
- The decision also lists cgroup and loginuid. Every user may read those two, and the probe keeps
  reading them itself, so the reader does not.

The output, exactly. ASCII lines ending in a line feed, fields separated by one space, every number
decimal:

| Line | Meaning |
| :- | :- |
| veldo-procread 1 cap=C | The first line, written after the reader has locked itself and before the table is read. The reader then waits for one byte. 1 is the format's version. C is 1 when the reader holds cap_sys_ptrace in its effective set, else 0 |
| p PID START | Opens the block of one process. START is field 22 of its stat file, its start time in clock ticks |
| t TID | Opens the facts of one task of the process. The first is the first thread, whose TID is the PID |
| c MAJOR:MINOR INODE | The working directory of the task |
| f FD MOUNT MAJOR:MINOR INODE | One open descriptor of the task: its number, its mount id, the device mountinfo gives for that mount id, its inode number. The device is a single hyphen when the process's mountinfo has no row for the mount id |
| m MAJOR:MINOR INODE | One mapped file of the process, after its last task. Lines of maps with inode 0 are left out; a pair may repeat |
| x FACT ERRNO | A fact that could not be read: of the task it follows for cwd and fd, of the process for stat, mnt, maps and task. ERRNO is the kernel's error number. x task 0 is a task that the second listing showed and the reader had not read |
| g | The process ended while it was read. Closes its block |
| end COUNT | The last line. COUNT is the number of p lines |

Threads that share a table would print the same lines once each. So a c or f line equal to one the
block already holds is not printed again. Every task still gets its t line, and the probe sees from
them that each was read. Nothing else is written to standard output, nothing to standard error, and
the exit status is 0. A block for the user manager, whose second thread sits in another folder, might
read:

```
p 2114 5127
t 2114
c 259:2 2
f 0 30 0:5 5
f 4 19 - 1058
t 2131
c 259:2 2278034
m 259:2 19937837
```

The checks, before every read. The probe makes checks 1 to 4 on the installed file before it
connects, because its trust in the output rests on that file. The unit's entry makes 2 to 4 again on
the descriptor it executes.

1. The reader's path and the socket's path are fixed in the probe. Neither is taken from the
   environment, the installation or the project.
2. The file is a regular file and no link, its owner is root, its group is the installation owner's
   group, its mode is exactly 0750, and every folder from / down to it belongs to root and is writable
   by root alone. The facts are read from the one open descriptor.
3. Its capability attribute holds exactly cap_sys_ptrace, permitted and effective, and nothing
   inheritable. The attribute is version 2, or version 3 with root id 0. Any other version or root id
   is refused.
4. Its SHA-256 digest, read through the same descriptor, equals the one in the installation's space
   section, key process_reader (6.8).
5. The kernel names one writer for the whole output: a process of the owner's uid whose status file
   shows exactly cap_sys_ptrace permitted and effective, NoNewPrivs 1 and Seccomp 2. The pidfd the
   kernel attached names that process alive before and after its status was read, at the header and
   at the end line. The first line says version 1 and cap=1. It is all that arrives before the probe
   sends its byte, and the probe sends the byte only after this check has passed for the header's
   writer.
6. The output is whole: every line is in the format, the end line is there with the right count, and
   after the probe has shut down its writing side the connection ends with nothing more. Where a row
   runs the reader directly, the exit status is 0 as well.

A reader that fails a check is not read, or its output is not used, not even in part. The probe's
answer then carries the reader's state (absent, or refused with the check that failed) and every
unread process is judged by the bound. The digest is not what stops the owner's own account from
changing the binary; root ownership of the file and its folders does that. The digest ties the
installed binary to the reviewed source: it is the digest the gate recorded when it built that source
(below), and not one the owner's shell produced. An agent that edits the digest in the installation's
file can only make the check fail.

How the probe uses the facts. For an item it lists the item's folder and everything beneath it,
following no link, and keeps the inode number of each entry, with its device for the record. On this
worktree that is 9,013 entries; the first form measured 0.3 seconds for it. A folder it cannot list
makes the item in use. Then, for each process it could not read itself:

- The reader's block is taken only when its process id and start time are the ones the probe reads
  for that process. A block with an x line, a missing block or another start time leaves the process
  unread, and the bound judges it.
- A process whose block is whole is read. It uses the item when the working directory or a descriptor
  of any of its tasks, or a mapped file, has an inode number in the item's set. It is named by process
  id, task and the fact that matched, with the device and inode number the reader printed. Otherwise
  it does not count, whatever its uid, its login or its parents: where it is has been read.
- The match is by inode number alone, in every case. The first form compared device and inode and
  said both are the same in every mount namespace. That holds for a bind mount and not for an overlay:
  a file opened through an overlay shows the overlay's own device with the real inode number, so a
  hold made through a container's or a sandbox's overlay of the item would have read as free. A btrfs
  subvolume, a pipe and a socket are the same kind of case. A match by number alone can only add a
  deferral, when a file elsewhere happens to have a number of the item's. The validation counted that
  on this host: 171,181 descriptor and map facts of 193 processes against this worktree, and none
  matched. The device stays in the deferral record, where it shows the owner such a match for what it
  is.
- A process the probe can read itself is judged from its paths, and from every task's: the working
  directory and the open files under /proc/<pid>/task/<tid>. A task it cannot read makes the process
  unread. A process table mounted with hidepid still makes the path in use; this ticket does not
  change that.

A deleted file that a process still holds open is not in the item's set and is not use: removing the
item takes nothing from that process.

The build, and the digest. The binary that gets the capability must be the reviewed source and
nothing else, and the owner's shell cannot be what vouches for it: an agent runs as the owner, and can
put another compiler first in the path or edit the source in the working tree. So the digest is fixed
before the owner builds anything. The build is reproducible: one source file, static, the compiler at
/usr/bin/cc, an empty environment, a temporary folder whose name the prefix map takes out. The
validation built the namespace helper twice that way, in two folders, and got one digest, equal to the
installed helper's. VELDO-0344's suite builds the reader twice the same way and fails when the two
digests differ. The proof bundle records the digest in proof/VELDO-0344/reader.sha256, with the
versions of the compiler and the C library. That file is part of what the owner approves with the
commit.

Install, by the owner, once, from the authority checkout's root. C stands for the commit the owner
approved, written as its full hash and not as a branch or a short form. H stands for the digest of
that commit's build, and the owner copies it from the review record they approved for C. H is not
read back from the checkout. The first line builds from the blob of that commit, not from the working
tree, and prints the digest of the build. It reads the blob with git's cat-file under
--no-replace-objects: git show follows replace refs, any process of the owner's can add one for C or
for the blob, and the line would then build another source without a word. The second is the one sudo
command, with H written into it:

```
d=$(mktemp -d) && g=$(id -gn) && /usr/bin/git --no-replace-objects cat-file blob C:scripts/veldo_procread.c > "$d/veldo_procread.c" && (cd "$d" && env -i PATH=/usr/bin:/bin /usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror -static -ffile-prefix-map="$d"=. -o "$d/veldo-procread" veldo_procread.c) && sha256sum "$d/veldo-procread"
(the sudo command is written once, in docs/veldo-procread-setup.txt and proof/VELDO-0344/owner-install.txt: root reads only the owner shell standard input into its own temporary file, compares it with H before anything else, and removes it when the comparison fails; see the review of VELDO-0344, finding 1)
```

The capability is set last, because a change of owner clears it, and only after root has compared the
installed copy with H. H comes from the review record the owner approved and not from the first line,
and not from proof/VELDO-0344/reader.sha256 as the checkout shows it: a digest read from the place
the source is read from would follow a substitution there. Whatever a process of the owner's account
did to the compiler, the source, the checkout's refs or the built file, the comparison then fails and
the copy is left with no capability. The setup text says the same in its first lines.

Then, without sudo, the owner installs the two units, starts the socket, writes H into the
installation's space section as process_reader, and runs the reader check:

```
python3 -I .veldo/control_space_probe.py reader-units && systemctl --user daemon-reload && systemctl --user enable --now veldo-procread.socket
python3 -I .veldo/control_space_probe.py reader
```

The check reads through the socket, as the service does. It prints the reader's state and reads one
undumpable process it starts itself, whose second thread sits in another folder.
docs/veldo-procread-setup.txt carries the same lines and says what a change costs. An upgrade of the
compiler changes nothing that is installed. It changes what the first line prints on that host, so a
new install waits until a gate run on that compiler has recorded the new digest and the owner has
approved it. An edit of the reader's source leaves the installed binary working with its old pin. When
the edit changes the output format, the probe refuses the old binary's output, and every item under
the home folder defers until the owner has installed and pinned the new build.

Uninstall, also the owner's. Any one of the three lines is enough, and after it the probe reports the
reader as refused or absent and judges by the bound:

```
systemctl --user disable --now veldo-procread.socket
sudo setcap -r /usr/local/lib/veldo/veldo-procread
sudo rm /usr/local/lib/veldo/veldo-procread
```

Then process_reader is set to none.

What an agent running as the owner can do with it. It can connect to the socket, or run the binary,
since it has the owner's group. It learns, for every process on the host: the process id and start
time, its thread ids, and the device and inode numbers of each working directory, of its open files
and of its mapped files, with descriptor numbers and mount ids. It learns no path, no file name, no
content, no memory, no command line, no environment and no address from maps, so nothing about the
memory layout of a root process. A number becomes a name only for a file the agent can already reach
and stat. So what it can newly answer is "does some process, root's included, have this file of mine,
or this file I can already see, open or mapped": which daemon has the password file open, or which
version of a library a root process maps. That is what lsof tells root, without the names. On a host
with one owner it is accepted, and the validation agreed.

It cannot make the reader do anything else. The reader takes no input, so there is nothing to steer. It
is static, so no library can be loaded into it. The kernel does not let a process attach to one that
holds a capability it lacks, so the agent cannot take the capability over through the reader. It can
kill the reader, fill or close the connection, or answer on the socket in the reader's place. The
output is then cut, or was not written by the reader, check 5 or 6 refuses it, and the item stays. An
agent inside Veldo's sandbox gets even less: the sandbox gives it a process table of its own and no
way to the socket.

What stays unread with the reader in use:

- a process that ends or changes while it is read, a thread started after the second listing included;
- a target whose AppArmor profile refuses the read, which is an x line;
- a kernel too old to show inode numbers in fdinfo (before 5.14; every block then has an x fd line);
- a kernel too old to hand over the writer's pidfd (before 6.5; the reader is then refused as a whole);
- a hidden process table.

Each of those is judged as before. Three more are not seen at all, by this reader or by the probe that
read paths. An overlay mounted with the xino option gives its files inode numbers of its own, so a
file held through such an overlay does not show the item's number. Files registered with io_uring, and
files in flight over a unix socket, are held without a descriptor in any table. So are the backing
file of a loop device and a swap file. The folder remover's rename and second probe do not see them
either. Removing the item does not take the data from a process that holds a file this way.

One more thing the reader takes on trust: that the /proc it reads is the host's. A process able to start
the real reader, with its capability, in a mount namespace that has another process table at /proc could
feed it a table of its choosing. A process of the owner's cannot do that today. It would need a user
namespace to make the mount, inside one the kernel does not grant the reader's file capability (the
attribute is version 2, or version 3 for root id 0, check 3), and the sandbox sets no_new_privs. The
reader's fstatfs check refuses a /proc that is not a process file system; it cannot tell the host's from
another namespace's.

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
walked into: that item holds its parent by its state. The walk starts at the item's own folder, for an
item of every disk kind. An item that is itself a git repository and is neither a worktree nor an
agent repository item holds itself as unrecorded (section 0.1), so a clone recorded under the wrong
kind is never handed to the folder remover. A worktree with a submodule is held this way
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
state what Discard removes from disk, that it is saved first, and the command that
brings it back (section 0.3 and 0.5; the first design had them say that Discard cannot be undone).
They list, for each worktree, the files Discard would remove
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
| Save | The changes are committed on a kept branch named for the ticket, authored as the owner's configured git identity. A worktree with no ticket gets a kept branch named for the run that owned it: the prefix space-saved, then the run's label. Then the worktree is removed by git's non-forced remove. When the tree is clean and only unlanded commits made the work unique, nothing is committed: the branch already holds them, it is kept, and the worktree is removed. Ignored files that are work are written to the snapshot store and never to the branch, and the remove runs only while those files still equal the snapshot. The worktree is moved to a marked name before that last look, so a file written by its path afterwards cannot go with the remove (0.3) |
| Keep | The item's state becomes kept. Nothing retries it and no second request is raised. Abandon on the console ends that |
| Discard | The discard remover runs: git's worktree remove with the force option on that one worktree. Rules 1, 2, 3, 4 and 6 still apply, and the remover refuses if the list of files differs from the list the owner was shown. No commit is lost. The branch is kept, so every commit on it survives. A detached worktree whose commits no ref holds gets a kept branch at its checked-out commit before the remove, and when that branch cannot be created the discard does not run (6.5). The uncommitted and untracked files the owner was shown are saved as a snapshot in the snapshot store before the remove, and veldo space restore brings them back (0.3, 0.5). The worktree is moved to a marked name before the last look and the remove, so a file written by its path afterwards cannot go with it (0.3). Nothing is lost |

Veldo never commits on its own. The commit in Save exists only because the owner's signed answer asked for
it. A snapshot is not a commit: it is files in the snapshot store, outside git (0.3). Discard's is
written on the owner's answer, and two are written with no answer, a review's scratch (below) and a
dead run's worker clone (0.3). Discard is the one forced removal in Veldo, and it is
allowed only after the owner's discard answer. Outside review worktrees there is one request per worktree:
later events for the same deferred item find the open request and add nothing. For a worktree in a plain
repository the request goes to the installation's owner.

Review worktrees. The lead's decision (e) has two halves.

Review scratch. A review worktree is a read-only checkout, so an untracked file in it that git does not
ignore is review scratch and not unique work. At the review's run finished Signal runs the review scratch
remover (6.5) on the worktree first, path by path under rules 1, 2, 3, 4 and 6, and then removes the
worktree by git's non-forced remove, which now finds nothing to refuse. Before the first path is
deleted the remover saves all of them as a snapshot in the snapshot store (section 0.3), so the
scratch can be brought back. Just before it deletes a file it compares the file with the manifest, and
a file that was added or rewritten since the snapshot stops the removal with the worktree deferred as
keep_failed. No request is raised. No force
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
   worktree found, the census of section 6.3. For each engine, the adapter's snapshot. The snapshot
   store under the state root is not such an entry: reconcile measures it, with the kept refs, for the
   console's totals, and it adopts and proposes nothing in it. What it does there is check: every keep
   record against the kept refs and every snapshot attempt it lists (0.3). A ref that does not resolve to
   its commit, a snapshot that is missing or whose manifest has another digest, and a store that is
   gone are reported as kept work missing. Folders no keep record names, the temporary ones included,
   are listed with their sizes.
3. Subscribe. The Docker adapter's event streams. On disk there is nothing to subscribe to: the creators
   report through the seam and the hooks, and the census reads the rest at events.
4. Compare, and for each difference do one thing:

| Found | Ledger | Result |
| :- | :- | :- |
| Thing | Matching item | Matched; size refreshed |
| Nothing, and nothing under the item's marked name beside the locator | Item present, declared, due or deferred | gone |
| Nothing at the locator, and a folder or a worktree under the item's marked name beside it | Item in any state | Never gone. Handled as the next row says |
| Half-removed folder under its marked name | Item removing | Removal completed. For a worktree or a private repository only when its keep record exists, every kept ref resolves and every snapshot attempt it lists is there with its digest; otherwise deferred as keep_failed (0.2). Where the removal compares files with a manifest, the completion compares them too, and a folder that comparison stops is renamed back to its locator and its item deferred as keep_failed. A worktree under its marked name is first set right with git's worktree repair and read again: equal to its snapshot and not in use, its removal is completed; otherwise it is moved back to its path and deferred as keep_failed. Where the way back is taken by something else, the item stays removing and both are reported |
| Worktree in a bound repository's list, under the project's worktree root, on a branch the branch pattern maps to a ticket | None | Adopted, owner that ticket |
| Worktree as above, branch maps to no ticket | None | Adopted, owner the project only. It ends on contained, project ended and Abandon |
| Worktree in a plain repository's list, under its worktree root | None | Adopted, owner the repository only |
| Agent repository under a worktree root, with the shared repository as its alternate | None | Adopted as an agent repository with the form agent, with its worktrees as children, owner by the branch pattern |
| Folder matching the project's build output patterns inside an adopted or recorded worktree | None | Adopted, parent that worktree |
| Folder directly under a declared build root whose name is the name of a worktree item | None | Adopted as build output, parent that worktree |
| Clone folder with a valid manifest under the state root | None | Its work tree is adopted as an agent repository with the form worker clone, owner the manifest's dispatch, main repository the one the manifest and the declarations name. Its root and its scratch folder are adopted as scratch, the root as the work tree's parent. Never the work tree as scratch |
| Item due or removing with a keep record, and the thing still whole at its locator | Item due or removing | The removal is attempted again from rule 1. It uses the newest attempt the record lists when that still has its digest and the item still equals it, and otherwise saves again under the next number and adds that attempt to the record (0.3). In report mode only for an item the owner confirmed or answered for |
| Run directory under the runs root named for a dispatch the store holds | None | Adopted as scratch, owner that dispatch |
| Session scratch folder matching the installation's pattern | None | Adopted as scratch, owner the session id in its name, with the project or plain repository the folder's name gives; when the name gives none, no project |
| Batch clone under the workspace root, named by a batch record the store holds | None | Adopted as an agent repository with the form batch clone, owner that batch, main repository the batch's. Never as scratch |
| Observation folder under the workspace root, named by a batch record the store holds | None | Adopted as scratch, owner that batch |
| Candidate workspace named by a landing record the store holds | None | Adopted as an agent repository with the form candidate workspace, owner that landing's lane. Never as scratch. One no record names is reported |
| Any folder a row above would adopt as scratch or build output that is itself a git repository | None | Reported, not adopted. A repository is never adopted as scratch |
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
  |  Process reader (a user unit of its own,                                                |
  |    started by its socket, one per read;                                                 |
  |    the one process with the capability)                                                 |
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
| Process reader (its own user unit, one instance per read) | Never. It has no store connection and takes no input | Never. It prints numbers from the process table and exits (7.1) |
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
| Modes | One row per project, per plain repository and for no project: report or act and since when. For a row in report mode: the last three calendar days, each marked clean or not with the reason (no event that day; a proposal marked wrong), the wrong-proposal records, and the Act button. Beside the button the row names what still blocks the switch: a day that is not clean, each unconfirmed pending group by kind with its count, a gate script without the space steps, no proof record for the modules and the git in use (0.7). The Ledger accepts the switch only when nothing is left. For a row in act mode: Back to report |
| Pending removal | Due and deferred items with the reason in words (in use by process 4412; uncommitted changes in 3 files), the event that will retry, and the open decision request when there is one. The review worktrees of one group are listed under their one request, each with its index and the three answers for it alone |
| Removed | The removal history: what, whose, which event, how much, free space before and after; for an engine pool the note that the host figure did not change. For a worktree and a private repository: how many refs were kept, whether a snapshot was saved and its size, and the restore command with the item filled in (0.5). Above the list, the totals: the count and the size of all kept refs and of all snapshots, the attempts no keep record names and the temporary folders counted apart. Both only grow until the owner drops some |
| Kept work missing | Shown at the top of the screen, and on the overview, only when there is something in it: each kept ref that no longer resolves to its commit and each snapshot that is missing or not whole, with the item, its ticket and the path it had, and a snapshot store that is gone or has another owner or mode. An entry stays until the ref or the snapshot is back or the owner drops that item's kept work (0.3) |
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
8. The owner runs veldo space prove on the host. It plants work in a scratch root of its own, drives every
   removal path at it and writes the proof record (0.7). Then, when core has three consecutive clean
   report days and no unconfirmed pending group, the owner switches core to act. The Ledger also reads the
   proof record and refuses without one that passed. The Ledger reads the three days and the pending
   groups from its records and runs the gate check on core's gate script, and it refuses the command if
   any of them fails; a proposal marked wrong starts the count again from the next day. From here
   core's removals happen at events and admission blocks core's runs and gates.
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

VELDO-0345 to VELDO-0348 were added on 2026-11-13 for section 0, the owner's rule that no work is
ever lost. They are the fiftieth to fifty-third tickets. On that day 0344 was the highest number a spec
file or a proof folder held on any of the repository's 508 refs or in any of its 79 worktrees. Proof
files on two remote refs name 0350 to 0390, which are another repository's specs, and other files name
numbers from 0401 up as examples. Nothing on any ref, in any commit message and in any ref name names
0345 to 0349.

VELDO-0349, the guard's rule, was added on 2026-11-13 by the lead's decision (section 13), the
fifty-fourth ticket. The count above had found the number free, and a second look that day found no
spec file, proof folder, ref name or commit message that holds it.

Build order: 0296, 0338, 0297, 0326, 0331, then 0298, 0299, 0330 and 0300 together, 0301, 0345, 0344,
then 0302, 0303 and 0305 to 0314 with 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341 in any
order, then 0347, then 0304, then 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319, 0346,
0349, 0320, 0332, 0325, 0339, 0321, 0322, 0348.

0345, the keep step, comes straight after 0301 and before every ticket that removes a worktree or a
private repository on a real host. 0347 comes after the creators and the census it corrects (0302,
0303, 0305, 0324). 0346 needs the console of 0319. 0349, the guard's rule, comes straight after
0346, because the one command it lets through is 0346's drop. 0348, the suite, is last because it drives every
removal path, and until it lands no scope can be switched to act.

The validation of section 0 added no ticket. Its criteria went into the tickets that build the parts
they belong to, and 0345, 0346 and 0347 each have five criteria since. The build order does not
change: 0347 comes before 0315, so the row for a batch clone that reconcile adopts is 0315's, and the
suite of 0348 drives it again.

0344, the process reader, comes straight after 0301: before any ticket that removes on a real host,
and long before 0320 (Confirm in report mode) and 0332 (the switch to act). Until the owner has
installed it, the probe judges unread processes by the bound, and on the measured host that defers
every item under the home folder. Since the validation of 7.1 the ticket has eight criteria. It is
kept as one ticket, because the reader, its unit, its build and the probe's matching are proved by one
suite and installed by the owner in one act.

0304, the boundary check, comes after 0302, 0303, 0324 and 0333 on purpose. Until those four have landed,
the paths in the Replaced table of 6.10 still hold removal primitives and the two removals by age, none
of them on the reviewed list, and the check would turn the gate red on its first run.

Tickets that touch protected paths and need the owner's recorded approval: 0302 and 0324 (the sandbox),
0309 (the gate script template, and the new helper added to the protected list), 0304 (its check is
called from scripts/verify.sh, policy.yaml:83), 0333 (the gate's leg timing), 0344 (the process reader's
source and its two unit files, which it adds to the protected list), 0349 (scripts/veldo-guard.sh and
its engine copy, both on the protected list already). 0325 produces a change to
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

AC1 is read more widely since the validation of 7.1: "a live process" means any thread of one, each
with its own working directory and its own open files. The ticket is built and its proof bundle
answers the text above, so the text stays, the change is recorded in the spec's History, and the row
and its falsifier are VELDO-0344 AC8.

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
| AC1 | Each creator's thing has a declared item before it exists and a present item after, with project, ticket, run and lane as owner; the rows cover the clone, the fleet worktree, the run directory, the candidate workspace, the batch clone and the batch's observation folder. The clone's work tree, the batch clone and the candidate workspace are declared as items of the kind agent repository, each with its form and its main repository, and never as scratch. The receiver's artifacts, receipts and token records are declared as evidence, never as scratch | Each of these turns a row of its own red. Declare after creating: the row that kills the creator between the two finds a folder with no item. Declare the batch clone as scratch: the row that reads the item finds the kind scratch and no main repository |
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
| AC2 | The check refuses a removal primitive outside the removers and the reviewed list of 6.10. A ref delete, a stash drop or clear, a reflog expire and a prune of objects are removal primitives, and each is refused everywhere but the owner's kept drop command | Restore the forced remove in the fleet module; the check stays green and its mutation row fails |
| AC3 | Every entry of the reviewed list names a function and a reason, and an entry whose function no longer holds a removal primitive fails the check | Accept a list entry that matches nothing; the stale-entry row fails |
| AC4 | The check refuses any function that deletes a folder, a single file or calls a remover and also reads a file's time or compares the clock with a threshold; this rule has no reviewed list | Restore the 30-day branch in prune_times; the check stays green and its mutation row fails |

### VELDO-0305 The run census and the run's space environment

Components: Receiver.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | At each run event every ignored folder git reports in the run's worktree that a committed ignore file of the project or a declared pattern covers becomes a build output item, whatever its name and depth; a keep entry is left out, and so is a folder only a personal ignore rule covers | Match the name target; the row's folder named otherwise has no item and fails |
| AC2 | An untracked path git does not ignore is never recorded as build output and makes the worktree unique work. So does an ignored path that no committed ignore file and no declared pattern covers, and a loose ignored file outside every build output folder | Record every untracked folder; the row's new source folder becomes build output and fails |
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
| AC1 | Each row of the table in 8.8 gives its result, including the agent repository, the build root folder named for a worktree, the plain repository and the session scratch. A clone folder's work tree, a batch clone and a candidate workspace are adopted as agent repository items with their form, and a folder that is itself a git repository is never adopted as scratch or as build output | Each of these turns a row of its own red. Adopt every folder under a root: the row with no provable owner gets an item. Adopt a batch clone as scratch: the row's clone holds a commit its main repository does not, its batch has ended and its scope is in act, and after reconcile the clone is gone and the commit is in no repository |
| AC2 | Reconcile completes a removing item and marks a missing one gone, and removes nothing else that was not already due. An item is marked gone only when nothing is at its locator and nothing is beside it under its marked name. A removing worktree or private repository is completed only when its keep record exists, every ref in it resolves and every snapshot attempt it lists is there with its digest; otherwise it is deferred as keep_failed. A folder under its marked name that the comparison with its manifest stops is renamed back to its locator, and a worktree under its marked name that is in use or no longer equals its snapshot is moved back to its path; each is deferred as keep_failed. An item that is due or removing with a keep record, and whose thing is still whole at its locator, is attempted again from rule 1 (VELDO-0345 AC5) | Each of these turns a row of its own red. Remove reported things: the reported fixture folder is gone. Mark gone by the locator alone: the row's worker clone was left under its marked name holding a file its snapshot does not, and after reconcile the item is gone while that folder is on disk |
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

Components: Signal, Removers (discard), Ledger (the effects). Depends on 0327 for the touchpoint and on
0345 for the snapshot. Review
worktrees are VELDO-0336, VELDO-0340 and VELDO-0342. The kept branch Discard makes for a detached worktree
is VELDO-0343.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A worktree deferred for unique work at ticket ended, project ended, worktree abandoned or released by its creator, and a worktree owned by a run that is not a review deferred at run finished, raises one request on the space disposition touchpoint with the three answers and the list of files; a later event for the same item raises no second one | Raise a request at every event; the row counts two requests and fails |
| AC2 | Save commits the changes on a kept branch named for the ticket, or for the owning run when the worktree has no ticket, authored as the owner's configured identity, and then removes the worktree without force. Ignored files that are work go to the snapshot store, outside git, and never to the branch, and the remove runs only while those files still equal the snapshot by path, mode and digest: a new or changed one refuses it, and the worktree stays with everything in it. Before that last look the worktree is moved to a marked name beside itself by git's worktree move, without force, and the in-use probe, rule 5 and the comparison are made under that name; a user or a difference moves it back to its path. Without a settled Save answer Veldo makes no commit | Each of these turns a row of its own red. Commit at the deferral: the row finds a commit with no settled answer. Run Save's remove without the comparison: the row adds a local settings file between the snapshot and the remove, and finds it neither in place nor in the snapshot. Make the last look at the worktree's own path: the row writes an ignored settings file by that path between the look and git's remove, and finds it neither in place nor in the snapshot |
| AC3 | Discard removes that one worktree with git's force option, only on a settled discard answer, only while the file list equals the list shown and rules 1, 2, 3, 4 and 6 pass. It first writes the snapshot of the uncommitted state to the snapshot store (VELDO-0345), runs only while the worktree still equals that snapshot, and does not run when the snapshot cannot be written, synced, read back or renamed into place. Before the remove the worktree is moved to a marked name beside itself by git's worktree move, without force; the in-use probe and the comparison with the snapshot are made again under that name, and a user or a difference moves it back to its path with everything in it. A Discard raised again after such a refusal saves under the next attempt number and leaves the earlier folder as it is. The branch and its commits are still there afterwards, and no commit is lost (VELDO-0343) | Each of these turns a row of its own red. Skip the list comparison: the row that adds a file after the request was shown loses it. Force the remove at the worktree's own path after the last look: the row writes a file by that path between the look and git's remove, and finds it neither in place nor restored |
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
| AC3 | docs/runbook.md gains the situations "the disk is full or a run is waiting for space", "a worktree is waiting for the owner's answer" and "getting removed work back", and passes the docs check | Name the measured host's project in the runbook; the docs check row fails |

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
| AC1 | A batch's discard removes its clone through Signal; a refusal is a deferral on the saved batch and request records and never an ignored error. Its observation folder is evidence (lead decision of 2026-11-15, section 13): it survives batch end, and verdict recorded, ticket ended and project ended are all on its end list | Leave the direct delete in place; the row with a process holding an open file in the clone finds the folder gone and fails |
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
| AC2 | The request's terms state what Discard removes from disk, that it is saved first, and the command that brings it back. They hold, for each worktree, the list of files Discard would remove and, for a detached worktree with commits no ref holds, the name of the kept branch those commits go to. The presentation shows both, and the Ledger raises no request that offers the discard pick without that list. The control path has no tier field and none is added | Raise the request with an empty list; the row that reads the presentation finds discard offered with nothing listed and fails |
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

Components: Git hooks, Kind registry, CLI (the run wrapper). Depends on 0311, 0313 and 0345.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | A worktree added detached with plain git inside a wrapped run is recorded with that run as owner, a review worktree when the run's station is review, and is removed at the run's run finished by git's non-forced remove, after its build output | Record it with the project as its only owner; the row finds the review worktree present after run finished and fails |
| AC2 | A worktree added on a branch inside a wrapped run keeps the owner its branch pattern gives and is still there after run finished | Give every worktree made inside a wrapped run to the run; the row's ticket worktree is removed at run finished and fails |
| AC3 | A review worktree with an untracked file git does not ignore is removed at run finished with no decision request and no force option; the file is saved in the snapshot store (VELDO-0345) and then deleted, as review scratch. Each file is compared with the snapshot's manifest immediately before it is deleted, and one that is not in the manifest or differs from it stops the removal, with the worktree deferred as keep_failed | Each of these turns a row of its own red. Defer it as unique work: the row finds the worktree present and a request raised. Delete the scratch without the snapshot: the row's stray file is neither in place nor restored. Delete without the comparison: the row rewrites the stray file after the snapshot, and finds the new content neither in place nor in the snapshot |
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
| AC3 | A group pick applies to every member still in the group and closes the group. Save commits each worktree's changes on a kept branch named space-saved and the review run's label and removes it without force; Keep sets each to kept; Discard saves each member's uncommitted state in the snapshot store first, removes each member whose file list equals the list shown and defers a changed one again, into a new group (VELDO-0342 AC3) | Skip the comparison per worktree; the row adds a file to one member after the request was shown, loses it and fails |
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

Components: Removers (discard), Ledger. Depends on 0318 and 0345; the group answers are 0340 and 0342.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Discard of a detached worktree whose checked-out commit no ref holds first creates a kept branch at that commit, named as Save names one, and records it as a branch item in state kept; afterwards the commit is reachable from that branch, and the worktree's uncommitted file is gone from disk and is in the saved snapshot (VELDO-0345) | Discard without creating the branch; the row finds the commit unreachable and fails |
| AC2 | When the kept branch cannot be created, because the name is taken by a branch that does not hold the commit or git refuses the ref, the discard does not run: the worktree and its files are still there, deferred as remove_refused | Run the remove after the failed branch write; the row finds the worktree gone and the commit unreachable and fails |
| AC3 | Discard of an agent's worktree leaves the agent repository and its branch in place, kept, with every commit on that branch | Remove the agent repository with the worktree; the row finds the branch's commit in no repository and fails |
| AC4 | Creating the kept branch makes no commit, Discard makes no commit, and neither sends a landing event: the row counts the same commits in the repository and the same event records before and after | Commit the worktree's files on the kept branch in Discard as Save does; the row finds a new commit on a branch and fails |

### VELDO-0344 The process reader

Components: Process reader, Reader units, Probes, Declarations reader. Depends on 0296, 0299 and 0330.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | With no reader at the fixed path, or one that fails a check (not a regular file, an owner other than root, a group or mode other than the installed ones, a folder on the way to it that another account owns or may write, a capability attribute other than exactly cap_sys_ptrace permitted and effective in version 2 or in version 3 with root id 0, no digest in the installation's space section, a digest other than that one, no socket, an output the kernel does not show as written by one process of the owner's that holds exactly that capability, whose status shows NoNewPrivs 1 and Seccomp 2, and that a pidfd names as alive before and after its status was read, anything but the one header line received before the probe has sent its byte, or a header that says it holds no capability), the probe does not use it, every unread process is judged as before this ticket, and the in_use facts name the reader's state and the check that failed. The reader writes its header only after it has set no_new_privs and installed its filter, and it writes the table only after it has read one byte on descriptor 1; the probe sends that byte only after it has seen the header's writer locked | Each of these turns a row of its own red. Skip the digest check: the row puts a program that prints an empty table in the reader's place, the undumpable process in the item is not counted and the item reads free. Accept any capability set that holds cap_sys_ptrace: the row's copy with cap_dac_read_search added is used. Accept version 3 of the capability attribute with any root id: the row's copy with another root id is used. Check the file and not its folders: the row's reader in a folder the owner may write is used. Ignore the header's cap field: the row's reader that says cap=0 is used. Take the output whoever wrote it: the row's stand-in listens on the socket, answers with an empty table, and the item reads free. Trust the process id without the pidfd: the row's stand-in writes an empty table and exits, the row answers the status read for its number as a real reader's, and the item reads free. Take bytes written before the writer was seen locked: the row's wrapper writes an empty table and then executes the real reader with its output on a socket pair, and the item reads free |
| AC2 | With the reader in use, a process of the owner's that is not dumpable counts for an item exactly when the working directory or an open descriptor of any of its threads, or a mapped file, is the item or beneath it, matched by inode number alone: the one in the item holds it, named by process id, thread id and fact with the device and inode number read, and the one outside it no longer counts | Each of these turns a row of its own red. Match the working directory only: the process that holds nothing but an open file beneath the item reads free, and so does the one that holds only a directory descriptor on the item. Leave out the maps: the process that only maps a file of the item reads free. Read the first thread's working directory only: the process whose second thread sits in the item with a file system state of its own reads free. Read the first thread's descriptors only: the process whose second thread holds a file of the item in a descriptor table of its own reads free. Match on device and inode: the row's descriptor that the reader printed with another device, or with a hyphen, reads free |
| AC3 | A root-owned process a login started is judged by the same facts: in the item it holds it, and elsewhere it does not count. A process with any fact the reader could not read (an x line, no block, or a start time other than the one the probe reads) stays unread and is judged by the bound of VELDO-0299. A folder of the item that the probe cannot list makes the item in use | Each of these turns a row of its own red. Take a block with an unread fact as read: the row's root-owned process, whose descriptors could not be listed and which holds a file in the item, reads free. Skip a folder that cannot be listed: the row's item, with a process holding a file inside a folder of mode 000, reads free |
| AC4 | The reader takes no argument and reads only the stat, mountinfo and maps entries of each process and the cwd and fdinfo entries of each of its tasks. It prints numbers only, in the format of design section 7.1. Its seccomp filter ends it on ptrace, process_vm_readv, process_vm_writev, pidfd_open, pidfd_getfd, kcmp, kill, tkill, tgkill, rt_sigqueueinfo and pidfd_send_signal, on an open with a write, create or truncate flag, on a write to any descriptor but 1, and on a call of another architecture. The filter does not limit which entries are opened for reading; the reviewed source does, and the digest ties the binary to it | Allow kill in the filter; the row's patched copy of the reader, which signals itself after the filter is in place, exits normally and the row fails. The row runs three more patched copies, for pidfd_getfd on a descriptor opened before the filter, for process_vm_readv and for an open for writing, and allowing any one of them in the filter lets that copy exit normally |
| AC5 | An output with no end line, an end count other than the number of blocks, a line outside the format, bytes after the end line or, where the reader is run directly, an exit status other than 0 is not used at all: the reader's state is refused, and every unread process is judged as before this ticket. The reader itself ends with no end line when a write fails. After its end line it waits, with one read on descriptor 1, until the probe has shut down its side, so the writer of a short output, one that fits in the socket's buffer, is still alive when the probe looks | Each of these turns a row of its own red. Use the blocks read before the cut: the row cuts the output before the block of the process in the item, and the item reads free. Go on after a failed write: the row gives the built reader a standard output that takes no more bytes, and finds an end line after the gap. Exit straight after the end line: the row lets the built reader finish a short output before it reads, and finds the writer gone when it looks |
| AC6 | The reader runs in a socket-started systemd user unit of its own, with no NoNewPrivileges and no sandboxing setting; the authority unit keeps NoNewPrivileges=yes, and every probe reads through the socket and executes no reader itself. The unit's entry checks the installed binary through one open descriptor and executes that descriptor. Where the reader is installed (requires.json), the reader check, run in a transient user unit with the authority unit's properties, reports the state used with cap=1 and reads an undumpable process it started in a folder, whose second thread sits in another; the row records how long the reader ran on that host | Each of these turns a row of its own red. Have the probe execute the reader itself, so that the check passes from the owner's shell only: the installed row, which runs the check under NoNewPrivileges=yes, reads cap=0. Check the path and then execute the path: the row swaps the file between the two and finds that the other program ran |
| AC7 | The reader built twice from the source of the commit under test, in two temporary folders, with /usr/bin/cc, an empty environment and the house build line, has one SHA-256 digest, and the proof bundle records it with the versions of the compiler and the C library (proof/VELDO-0344/reader.sha256). The owner's install lines in the setup text build from the blob of a commit named by its full hash, read with git's cat-file under --no-replace-objects, and root's line compares the installed copy with a digest written into it before it sets the capability. The setup text says that this digest is copied from the review record the owner approved for the commit and is not read back from the checkout | Each of these turns a row of its own red. Drop the prefix map from the build line: the two folders give two digests. Take the compiler from the path: the row puts a stand-in cc first in the path and finds the stand-in's output. Put setcap before the digest comparison in the setup text: the row that reads the lines finds the order wrong. Read the blob with git show: the row adds a replace ref for the blob in a fixture repository, runs the first line there and finds the other source built |
| AC8 | The probe's own reading of a process it may read covers every thread: the working directory and the open files of each task under /proc/<pid>/task. A process with a task it cannot read is unread. This widens VELDO-0299 AC1, whose text is not edited; the change is in that spec's History | Read the first thread's working directory only; the row whose second thread sits in the path with a file system state of its own reads not in use and fails |

The four cases the owner named, and the row that holds each: the reader absent, fail closed (AC1); the
reader present and an undumpable process of the owner's in the item holds it (AC2); a root-owned
process the owner started holds it (AC3); a tampered reader is refused (AC1's falsifiers, and AC5 for
its output). The validation's points: B1 is AC6, B2 is AC2 and AC8, B3 is AC7, R1 is in AC2, R2 is
AC4, R3 is the falsifiers of AC1 to AC3, R4 is in AC6. The second validation's points: the pidfd is
in AC1, the reader's wait and the short output are in AC5, the run time is recorded by AC6's row, and
the replace refs and the source of the digest are in AC7. The final check's point, a writer that
executes the reader in its own place, is in AC1.

### VELDO-0345 The keep step: kept refs and the saved snapshot

Components: Keeper, Removers, Ledger (the keep record). Depends on 0297, 0299, 0300 and 0330. It builds
sections 0.2 and 0.3, and it adds the keep step inside the worktree remover and the private repository
remover of 0300. Since the validation of section 0 it has five criteria: AC5 holds the snapshot's
failure, crash and retry paths.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Before git's worktree remove runs, the worktree's checked-out commit, each of its own refs, each commit an operation in progress names and each commit only its HEAD log names is on a kept ref under refs/veldo/kept/<ticket>/<item>/ in the main repository, read back, and listed on the item's keep record; the ledger refuses the outcome removed for a worktree or a private repository that has no keep record. For an agent's worktree the main repository is the shared repository: the commits are fetched from the agent repository and the kept refs are written there, and none is written in the agent repository | Each of these turns a row of its own red. Write the refs after the remove: the row kills the remover between the two and finds the commit the HEAD log named in no ref. Write an agent worktree's kept refs in its agent repository: the row removes the worktree and then the agent repository, and finds the worktree's kept head under its own item's name in no repository |
| AC2 | Before a private repository is removed, every ref it has, every stash entry, its HEAD and each commit only a log names is fetched into the main repository under the item's kept refs, and afterwards each of those commits is read from the main repository alone | Fetch the branches only; the row's second stash entry is in no repository after the removal and the row fails |
| AC3 | When a ref cannot be written, exists at another commit or reads back as another commit, when the fetch fails, when the main repository is not at its path any more, or when a private repository names no main repository, nothing is removed, by an event or by reconcile, and the item is deferred as keep_failed with the ref and git's words. A second attempt after a crash finds the refs it wrote and passes. Rule 5 does not count a kept ref as a ref that holds a commit | Each of these turns a row of its own red. Call the remover after a failed write: the row makes the main repository's refs unwritable, and finds the worktree gone and its commit unreachable. Go on when the main repository is gone: the row moves the main repository away, sends the ending event, runs reconcile, and finds the worktree gone |
| AC4 | The saved snapshot is plain files with a manifest in the snapshot store under the state root, outside every repository: the tracked edits, the staged state and the untracked files, the ignored ones that are work included, each with its mode and its SHA-256. Writing it changes neither the worktree, nor its index, nor the repository's stash entries, and adds no object to any repository's object store. It is read back and compared before the keep record is written. The snapshot store is protected in every installation, and no rule lets a remover take a path in it | Each of these turns a row of its own red. Write it as a commit on a kept ref: the row plants a marker in an ignored settings file and finds the marker in an object of the main repository after the Discard. Write it with git's stash command: the row compares the worktree and the stash entries before and after, and finds the worktree emptied and an entry added. Leave the store off the protect list: the row declares a folder of the store as scratch, sends its ending event and finds the snapshot gone |
| AC5 | A save that fails or stops half way removes nothing: when the store cannot be written, when its pool fills in the middle of a file, when a write is short, when a read back differs, when a sync or the rename fails, the item is deferred as keep_failed with everything in place, and what the attempt wrote stays under its temporary name. Each attempt writes a numbered folder of its own, <state root>/space-saved/<ticket>/<item>/<n>/, that is never replaced and never deleted; the keep record lists every attempt it was given, a later keep write for the item adds refs and attempts and removes none, and a folder no record lists and a temporary one are kept and counted. A retry uses the newest attempt the keep record lists when its manifest has the recorded digest and the item still equals it, and otherwise writes the next number and adds that attempt to the record. With the process killed inside the snapshot write, after the rename and before the keep record, and after the record and before the remover, the next attempt ends with the item removed once and its snapshot whole, or with the item in place; reconcile's part in that is VELDO-0315 AC2 | Each of these turns a row of its own red. Go on after a short write: the row fills the store's pool in the middle of a file, and finds the worktree gone and the file in no place. Make room for a retry by deleting the existing snapshot folder: the row kills the remover between the delete and the rename and finds no copy of the file. Use the snapshot the record names without comparing: the row changes a file after the kill, and finds the new content neither in place nor restored. Keep only the newest attempt on the record: the row stops a review scratch removal after its first delete, retries, restores, and finds the first deleted file missing while restore said success |

### VELDO-0346 Getting removed work back: kept, restore and drop

Components: CLI, Ledger (restore, drop kept), Keeper (the check of keep records), Reconciler, API,
Console. Depends on 0319 and 0345. It builds section 0.5 and the watch on the snapshot store of 0.3.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | veldo space kept lists, for each removed worktree and private repository, its ticket, the path it had, the event that removed it and each kept ref with its commit, and says of each ref whether it still resolves and of each snapshot attempt the keep record lists whether it is still there and whole. With no ledger reachable it lists the same refs from the repository alone | Read the ledger only; the row with the authority down gets an empty list and fails |
| AC2 | veldo space restore adds a worktree at the path the item had, or at the path given, at the kept head, and applies every snapshot attempt the keep record lists, the oldest first, so that the later one wins where two hold the same path: after a Discard and a restore the tracked edits, the staged state, the untracked files and the ignored files that are work are back byte for byte with their modes. Whether there is a snapshot is read from the keep record alone. It refuses, adding nothing and saying what is missing, when something is at the path, when any attempt the record lists has its folder or manifest missing or a manifest with another digest than the record holds, when a saved file does not match its manifest, and when a manifest path is absolute, holds a .. part or resolves outside the target path. It leaves the kept refs and the snapshots in place | Each of these turns a row of its own red. Restore the head without the snapshot: the row's untracked file is missing. Apply the snapshot only when the folder is there: the row deletes the snapshot, restores, finds the head without the untracked file, and the command said success. Copy a manifest path as it is written: the row's manifest names a path with a .. part, and a file is written outside the target. Apply the newest attempt only: the row's review scratch removal stopped after its first delete and was retried, and the restore leaves the first deleted file missing |
| AC3 | Only veldo space kept drop removes a kept ref or a snapshot. It is the owner's signed command, it lists the commits that would no longer be reachable and every file of every attempt folder of the item, the folders no record lists and the temporary ones included, before it acts, it removes the item's whole folder in the store, and it is refused from every host principal | Each of these turns a row of its own red. Accept drop from space-runner: the row that sends it finds the refs gone. List only the attempts the record lists: the row's item has one more attempt folder that no record lists, and drop removes a file its listing did not show |
| AC4 | The console's Removed section and the space.kept read show, for each removal, the number of kept refs, whether a snapshot was saved and its size, and the restore command with the item filled in; and for the installation the count and the size of all kept refs and of all snapshots | Leave the kept refs out of the read; the row that expects the restore command beside the removed worktree finds none and fails |
| AC5 | Reconcile and veldo space kept check every keep record against the disk: each kept ref resolves to its recorded commit, every snapshot attempt the record lists is there, and each manifest has its recorded digest. What fails is reported under space.reports as kept work missing, with the item, and is shown at the top of the console's Space screen until the ref or the snapshot is back or the owner drops that item's kept work. A snapshot store that is gone, or whose owner or mode is not the installation owner's and 0700, is reported the same way. Snapshot folders no keep record names, whole or temporary, are listed under the item whose folder holds them, with their sizes, and are counted in the totals. They go with that item's drop (AC3), and nothing else is proposed for them | Each of these turns a row of its own red. Check the kept refs only: the row deletes the snapshot store, runs reconcile and finds no report. Check the newest attempt only: the row deletes the first of an item's two listed attempts, runs reconcile and finds no report. List only what keep records name: the row's item has an attempt folder no record names, and veldo space kept does not show it |

### VELDO-0347 Work the first rules did not see: ignored files, repositories in any folder, evidence

Components: Probes, Signal (rules 5 and 6), Removers, Kind registry (one row), Ledger (the form of an
agent repository item), Clone provisioner, Batch, Landing line. Depends on 0302, 0303, 0305, 0324 and
0345. It builds section 0.1 and 0.4 where they go past what VELDO-0299 and VELDO-0330 built.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | Rule 5 refuses a worktree that holds an ignored file which is not build output: a loose ignored file outside every build output folder, and a path only a personal ignore rule covers. A path whose rule cannot be traced is counted the same way | Leave ignored paths out of case 3; the row's local settings file goes with git's non-forced remove and the row fails |
| AC2 | A git repository beneath a scratch item or a build output item holds it, as unrecorded, unless it is a clean clone: no uncommitted and no untracked file, no stash, every ref and its HEAD held by one of its own remote-tracking refs, no log entry whose commit those refs do not reach, and, for a remote that is a path on this host, each of those commits present in that repository now. One that cannot be read, one whose local remote cannot be read, and a folder that cannot be listed, hold the item | Each of these turns a row of its own red. Look beneath worktrees and agent repositories only: the row's clone with an unpushed commit in a session's scratch is deleted. Leave the logs out: the row's clone whose only unpushed commit a reset left in its HEAD log is deleted. Take a remote-tracking ref at its word: the row writes one by hand for a commit its local remote does not hold, and the clone is deleted |
| AC3 | A worker clone, a batch clone and a candidate workspace are items of the kind agent repository with their form, never scratch, and are removed as private repositories: the keep step records every commit in the main repository first. A batch clone or a candidate workspace whose work tree holds an uncommitted or untracked file that is work is deferred as unique work and raises one request on the space disposition touchpoint, as a worktree does. A worker clone of a run that has ended is not deferred for such files: they are saved in the snapshot store, each file is compared with the manifest immediately before it is deleted, and the clone is removed with no request. When that comparison stops the removal, the folder remover renames the folder back to its locator before the item is deferred, so the item keeps its id, the next attempt saves what is left, and reconcile does not mark it gone | Each of these turns a row of its own red. Remove a clone by the folder remover alone: the row's commit that the runner never brought across is in no repository. Remove a worker clone without the snapshot: the row's uncommitted file is neither in place nor restored. Delete a worker clone's files without the comparison: the row rewrites a file after the snapshot, and finds the new content neither in place nor in the snapshot. Leave the folder under its marked name at that stop: the row runs reconcile, and finds the item marked gone and the rewritten file in a folder no item names |
| AC4 | An evidence file is removed only when its digest, read again at the removal, is the digest of a blob the store holds or of a file in a commit the trunk or a kept ref reaches; a store or a commit that cannot be read is no copy | Use the digest recorded at the last measurement; the row changes the file after it was measured, finds the changed file gone and fails |
| AC5 | The look of rule 6 starts at the item's own folder: an item whose folder is a git repository and whose kind is neither worktree nor agent repository holds itself, as unrecorded. The kind registry has a row for an agent repository item whose form is a worker clone, a batch clone or a candidate workspace, which ends at the events its creator sends; an item with no form ends only on the agent repository's own events | Each of these turns a row of its own red. Look beneath the item only: the row's scratch item whose own folder is a repository with an unpushed commit is deleted. Give an item with no form the clone's row: the row's agent repository with its worktree still in place is made due at run finished |

### VELDO-0348 The no-work-is-lost suite, and act mode

Components: the suite, CLI (space prove), Ledger (the proof record, mode), Signal. Depends on 0320, 0339,
0344, 0346 and 0347. It builds section 0.7. It joins VELDO-0332, VELDO-0339 and VELDO-0344 as what must
be there before any scope can be switched to act.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The suite drives every removal path of section 0.7 at every kind of work of section 0.1, in every shape of that section's table: nested, adopted, an agent worktree and then its repository, linked, locked, unreadable, main repository gone, snapshot store, retry and restore. After each drive every planted thing is in its place byte for byte, or comes back byte for byte through veldo space restore from what the removal left; a restore that says it succeeded while a planted file is absent fails the row; the suite's own copies are never read. The paths, kinds and shapes are data, and a remover or a kind of work with no row fails the suite | Run Discard without the snapshot; the Discard rows find the untracked file neither in place nor restored and fail |
| AC2 | A file added after the probe, a process that opens a file after the first probe, a branch moved between the probe and the remove, a file added between the snapshot and the forced remove, an ignored file added between Save's snapshot and its remove, and a file of review scratch or of a dead run's worker clone rewritten between the snapshot and its own delete each leave the work in place. A write by the worktree's path between the last look and git's remove, in a Discard and in a Save, either fails for the writer or leaves its file in place or in the snapshot. A worker clone whose removal the comparison stopped is back at its locator, and reconcile run afterwards does not mark it gone. With the process killed at each step boundary of section 0.2, the two snapshot boundaries included, and of the folder remover, and reconcile run afterwards, every planted thing is in place or comes back | Complete a removing item at reconcile without its keep record; the row killed before the refs were written finds the worktree gone and its commit unreachable, and fails |
| AC3 | Each mutation of section 0.7 turns a row of the suite red and is registered with the gate's mutation check: a kept child that does not hold, a stash counted as a holding ref, no look beneath a worktree, a private repository compared with itself, an unreadable worktree read as unlocked, an unopenable scratch read as free, the keep step skipped, the remove run after a failed keep, Discard without the snapshot, a snapshot written into a repository's object store, a removing item completed with no keep record, the remove run after a failed snapshot, review scratch deleted without the snapshot, a file deleted without the comparison with its manifest, an existing snapshot folder replaced on a retry, Save's remove run with an ignored file the snapshot does not hold, a restore that applies the snapshot only when its folder is there, a clone adopted as scratch, no look at an item's own folder, an agent worktree's kept refs written into its agent repository, a clean clone read without its logs, a keep record that holds only the newest attempt, a folder left under its marked name when the comparison stops its removal, and a Discard or a Save that removes the worktree at its own path | Drop the nested rows from the suite's data; the mutation that skips the look beneath a worktree leaves the suite green and the mutation check fails |
| AC4 | The switch to act is refused as space_act_unbuilt naming VELDO-0348 until this ticket lands. From then it is refused unless the ledger holds a proof record that passed, written by the owner's veldo space prove on this host, whose digest of the space modules and whose git version are the ones in use; the refusal names what does not match. A scope already in act with no matching record writes due and removes nothing | Accept any proof record that passed; the row changes one space module after the proof, switches a scope to act and fails |

### VELDO-0349 The guard keeps hands off the kept store

Components: Guard hook. Depends on 0346. It builds the guard's rule of section 0.3, by the lead's
decision of 2026-11-13 (section 13). scripts/veldo-guard.sh and engine/scripts/veldo-guard.sh are
protected paths, so the change lands with the owner's recorded approval.

| AC | Claim | Falsifier |
| :- | :- | :- |
| AC1 | The guard hook refuses, with exit status 2 and before the command runs, a shell command whose text names the snapshot store: its path under the state root, written in full or with the home folder written as ~ or $HOME. The refusal says that the store is kept work and names veldo space kept, veldo space restore and veldo space kept drop. When the guard cannot read the state root, it refuses a command that holds the word space-saved | Each of these turns a row of its own red. Leave the rule out: the row's planted command, a recursive delete of the store's path, is allowed. Stand down when the state root cannot be read: the row hides the state root from the guard, plants the same command, and it is allowed |
| AC2 | The guard hook refuses the same way a shell command whose text holds refs/veldo/kept, whatever the command does with it | Refuse only a ref delete: the row's planted command that points a kept ref at another commit is allowed |
| AC3 | veldo space kept drop is allowed when it is the whole command, also when it names the store or a kept ref. A command that joins anything to it, by a separator, a pipe, a new line or a substitution, is judged like any other | Each of these turns a row of its own red. Refuse every command that names them: the row's drop command, with its item given by its kept ref, is refused. Allow any command that holds the words veldo space kept drop: the row's command that follows them with a delete of the store is allowed |
| AC4 | A command that names neither the store nor the kept refs is untouched: for a command the guard has never judged and for one it judges today, the exit status and the output are those of the guard before this ticket. veldo space kept and veldo space restore with an item are allowed. The three copies of the guard are byte for byte the same | Refuse on the word kept alone: the row's veldo space kept command, and its git command on a branch named kept-notes, are refused |

The three cases the lead named, and the row that holds each: a planted command that names the store
is refused (AC1, and AC2 for the kept refs); veldo space kept drop is allowed (AC3); a command that
names neither is untouched (AC4).

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
| The reader runs in a socket-started systemd user unit of its own, and every probe reads through the socket | The lead's decision on B1 of the validation. The authority unit sets NoNewPrivileges=yes, under which the kernel grants no file capability, so a reader the service's own child started would hold nothing. A user unit beside the authority unit needs no sudo, no second account and no system service, and the authority unit keeps its hardening |
| The probe takes the reader's output only from the process the kernel names as its writer | Not asked by the validation; taken in this revision. Any process of the owner's can listen on a socket in the owner's runtime folder, so the digest of the installed file says nothing about who answers. The kernel's own record of the writer, a process of the owner's with exactly cap_sys_ptrace, does |
| Every thread of a process is read, by the reader and by the probe's own reading | B2 of the validation, measured: the entries under /proc/<pid> are the first thread's, and a thread with a working directory of its own in the item read as free |
| The reader is built from the blob of the approved commit, and root compares the installed copy with the digest the gate recorded | B3 of the validation. The first form pinned whatever the owner's shell had built, and an agent runs in that shell. The build is reproducible, so the digest can be fixed in the proof bundle before the owner builds |
| A fact matches an item by inode number alone, and the device stays in the deferral record | R1 of the validation. Through an overlay a file shows the overlay's device with its real inode number, so a match on both read such a hold as free. A number alone can only add a deferral, and on this host it added none in 171,181 facts. An overlay with the xino option stays unseen, and 7.1 says so |
| One capability stays, cap_sys_ptrace | The lead's answer to the point of section 15, and the validation's. cap_dac_read_search would let the reader, or a mistake in it, read every file on the host, and would buy only paths |
| Unread processes are read by a separate reader with one file capability, not excused by a list of names and not by a capability on the service | The owner's decision (Telegram 41204 and 41205). A name is whatever a process calls itself, and the re-review excused a renamed process with one. CAP_SYS_PTRACE on the service would let the whole service attach to any process; on a reader that takes no input and is shut in by a seccomp filter it can only read |
| The reader prints device and inode numbers, never paths | Measured: cap_sys_ptrace alone gives the working directory, the maps and each descriptor's inode number, and does not list the descriptors' paths. Numbers are also the same in every mount namespace, where a path is not, and they tell whoever runs the reader no file name. The price is that the probe lists the item's files to compare, 0.3 seconds for a worktree of 9,011 entries |
| The reader is C, static, built like veldo-userns | A file capability needs a binary of its own. The repository already builds, reviews and gates one static C helper, and a second toolchain for 200 lines would be a dependency with no gain |
| The reader's digest is in the installation's space section, and its path is fixed in the probe | The path cannot be pointed elsewhere by a file an agent can edit. Root ownership is what keeps the binary from being changed; the digest refuses a binary that is not the reviewed source as the gate built it |
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
| No work is ever lost is the first rule, and it is a rule about saving, not only about refusing | The owner's rule (Telegram 41209). The first design protected work by refusing to remove. That left every forced or silent removal as a place to lose it: Discard, review scratch, an ignored file, a clone called scratch. Section 0 makes each removal save first |
| The keep step always writes, with no test of whether another ref holds the commit | A containment test is a probe, and the reviews found probes wrong. A ref that is always written cannot be wrong in that way, and it costs one line in a file |
| The keep step is part of the removers, not an eighth rule | The seven rules, their order and their numbers are built and cited in forty places. A step between rule 6 and the tool changes none of them |
| A kept ref is never a reason to remove | Rule 5 does not count it among the refs that hold a commit. Otherwise writing a kept ref for one worktree would let another one go without the owner's answer |
| A snapshot is stored outside git, as plain files with a manifest under the state root, never in a repository's object store. Commits stay on kept refs | The lead's answer (4) of 2026-11-13. A snapshot can hold an ignored settings file with a secret in it, and in git the secret scanner and every agent repository's alternate would see it. The first form, a commit in git's stash layout, is withdrawn. The price is that plain git no longer restores a snapshot; veldo space restore does, and without Veldo the working files are copied back by hand |
| Review scratch is saved and then removed, still with no request | The lead's answer (1): decision (e) stays. Saved means not lost |
| Unlanded commits still raise a request | The lead's answer (2): keep asking, as designed. The keep step makes the commit safe; it does not make the question go away |
| A dead run's worker clone with uncommitted files is saved and then removed, with no request | The lead's answer (3): as review scratch. The answer names worker clones, so a batch clone, a candidate workspace and an agent repository still raise a request |
| Session scratch goes at the session's end and is saved nowhere | The lead's answer (5): as designed. A project that wants a folder left alone names it in its keep list |
| Kept refs and snapshots only grow. The console shows the count and the size of each, and nothing drops one without the owner's rule | The lead's answer (6). The one way out is the owner's signed drop command |
| A snapshot attempt has a numbered folder of its own, never replaced and never deleted | From the validation of section 0. A second snapshot for one item is a normal case: a Discard deferred after its first, a crash before the keep record. A rename onto the first folder fails, and deleting it first leaves a moment with no copy. A folder nobody uses again costs space, and space is what the owner drops when they choose |
| A failed or half-finished save leaves what it wrote in place | Deleting it would be a remover working in the snapshot store, which the protect rule forbids for good reason. The folder keeps its temporary name, is counted and is listed |
| Files removed one by one are compared with the manifest just before each delete | Review scratch and a dead run's worker clone go with no owner looking at a list, and rule 4 does not see a process that wrote a file and closed it. Discard keeps its one comparison before git's forced remove, which is one command |
| A restore reads whether there is a snapshot from the keep record, and refuses when it cannot find or verify it | Read from the disk, a deleted snapshot looks like an item that never had one, and the restore would bring back the head and call it done |
| The loss of a kept ref or a snapshot is detected and reported, not prevented | An agent outside the sandbox runs as the owner, and nothing in Veldo's own code stands between that account and a folder or a ref. Reconcile and veldo space kept check every keep record, and the report stays until the work is back or the owner drops it |
| Every private repository is an item of the kind agent repository, told apart by a form; there is no eleventh kind | From the validation of section 0, which offered both. The kind picks the rules, the look and the remover, so one kind means a clone gets every protection an agent repository has without each place being told. The form picks only the lifecycle row, and an item with no form ends on fewer events, not more |
| An item of another kind whose own folder is a git repository holds itself | The backstop for the decision above: a creator or an adoption rule that still says scratch cannot hand a repository to the folder remover |
| An agent worktree's kept refs are written in the shared repository | Of the two ways the validation offered, this one keeps "a kept ref is never deleted or moved" true. Written in the agent repository they were carried across under another name when that repository went, and the worktree could no longer be restored |
| A clean clone is judged on its logs too, and a local remote is read | A reset leaves a commit named by a log alone. A remote-tracking ref is a claim about the last fetch that anyone can write. A remote on another host is not read, and 0.9 says what that leaves |
| The probe holds the reader's writer by a pidfd, and the reader waits for the probe before it exits | From the second validation of 7.1. A process id can be handed out again between the write and the look; a pidfd cannot. Measured on this host: the kernel attaches one to each part, and it reads as ended for a writer that has gone |
| The install line reads the source with replace refs off, and the digest comes from the review record | git show follows a replace ref that any process of the owner's can add. A digest read back from the same checkout would follow the same substitution |
| The keep record lists every snapshot attempt, and no later write takes one off | From the final check (14.8). With one snapshot in the record, a retry after a removal that had already deleted some files replaced the attempt that held them, and a restore said success without them. Restore applies every listed attempt, the oldest first. It may bring back a file the owner had deleted between two attempts, and that is the cheaper mistake |
| The reader locks itself before its header and writes the table only after the probe's byte, and the probe requires NoNewPrivs 1 and Seccomp 2 of the writer | From the final check. Executing a program keeps the process and its pidfd, so bytes written before the execution were credited to the reader. A process holds the capability and a filter together only by executing the installed binary first, and the filter refuses another execution. The writer check stays, as the check asked |
| The guard hook refuses a shell command that names the snapshot store or refs/veldo/kept, except veldo space kept drop. One ticket, VELDO-0349, after 0346 | The lead's decision of 2026-11-13 on the question section 15 held. The cost is one rule in a hook that already reads every command, and the owner's rule is about exactly this work. Detection stays, because the guard reads the text of a command and does not see what a program the agent wrote does. scripts/veldo-guard.sh is a protected path, so the change lands with the owner's approval |
| An ignored file that cannot be shown to be build output is work | git's non-forced remove deletes ignored files silently. The project's committed ignore rules and its declared patterns say what a build makes again; a person's own ignore rule does not |
| Worker clones, batch clones and candidate workspaces are private repositories | Each holds commits the shared repository may not have. Removed as scratch, a failed run's commits went with the folder |
| A batch's observation folder is evidence, never scratch. Its end list is the evidence kind's own, copied from the kind registry at declaration; declare takes no end list from its caller (4.1, 6.1) | The lead's decision of 2026-11-15, from the review of VELDO-0324. The reviewer reads the folder after the batch ends, so batch end must not remove it. It stays past run finished; verdict recorded, ticket ended and project ended are all on its list, and the first of the last two removes it. An end list chosen by the creator dropped ticket ended and project ended, and such folders would never have been removed |
| The criteria of the eight built tickets are not edited | A proof bundle answers the criteria it was written for. What the rule asks of built code is in VELDO-0345, 0347 and 0348, and noted in each built ticket's History |
| Act mode needs the suite passed on the host, for the modules and the git in use | What git's remove deletes, and what its status and its ignore rules report, are facts of the git on that host. A pass in the gate is about the build host |

Left out, each a later ticket if wanted: a second host; build caches shared between worktrees; shrinking a
container engine's disk image; removing contained branches; a per-ticket space budget; a "superseded"
transition; removal of unlabelled Docker objects.

## 14. Validation response

Five validations of the design, all of 2026-11-13, one of section 7.1 alone, and one of section 0
with 7.1's second revision, all in the owner's notes repository under research/codex-reviews. Every
point was checked against the code before it was taken. The fifth is in 14.5, the one of 7.1 in 14.6
and the one of section 0 in 14.7; 14.1 to 14.4 run from the fourth back to the first and keep their
numbers, because other sections cite them.

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

### 14.6 The validation of section 7.1 (design-veldo-0344-validation-2026-11-14.md)

Verdict CHANGES: three blocking points and four smaller ones, all taken. The validation accepted the
shape, the measurement and the one capability. Where the lead decided between ways, the row says so.

| Point | Checked | Where it is fixed |
| :- | :- | :- |
| B1 the service's NoNewPrivileges leaves the reader with no capability | True: veldo-authority.service line 17, and the space worker is the service's child. The lead took the validation's first way, a socket-started user unit for the reader. Measured here with transient user units: a plain one has NoNewPrivs 0 and the full bounding set. One thing follows that the validation did not raise: a socket in the owner's runtime folder can be answered by any process of the owner's, so the probe checks the kernel's record of who wrote the output. Measured here: SO_PASSCRED gives the writer's process id for each part | 7.1 ("Where the reader runs", "Who is on the other end", checks 1 and 5), section 3 (Reader units, Probes), section 9, section 13; ticket 0344 AC1 and AC6 |
| B2 a thread with its own working directory or descriptor table is not read | True, by the validation's measurement. The reader reads every task and prints a t line for each; equal lines within a block are printed once. The probe's own reading gets the same fix | 7.1 ("Every thread", the format, "How the probe uses the facts"), section 7 (the note on process use); ticket 0344 AC2 and AC8, ticket 0299 (the note under its table, and its spec's History) |
| B3 the install pins whatever the owner's shell built | True: the first line took cc from the path and the source from the working tree. The validation's lines are taken, with git called by its full path and the unit lines added | 7.1 ("The build, and the digest", the install lines), 6.8, section 13; ticket 0344 AC7 |
| R1 device matching misses a hold made through an overlay | Taken as recommended: inode number alone in every case, the device in the deferral record. The xino case is named among what stays unseen | 7.1 ("How the probe uses the facts", "What stays unread"); ticket 0344 AC2 |
| R2 "enforced by the kernel" overstates the filter | True: a filter cannot see the path of an open. The bullet now says what the kernel enforces and what only the source and the digest do, and lists the calls refused | 7.1 (the reader's filter); ticket 0344 AC4 |
| R3 one falsifier where a claim names many | Taken: the capability set, the folder chain, the cap=0 header, the maps, the directory descriptor, the two thread rows, the device rule and the unlistable folder each have a falsifier. The attribute version is stated. The hyphen rule is gone with R1, and its row is the device row | Ticket 0344 AC1, AC2 and AC3; 7.1 check 3 |
| R4 hash and run the same file | Taken, in the place where the reader is now executed: the unit's entry checks one open descriptor and executes it | 7.1 ("Where the reader runs", check 2 and 4); ticket 0344 AC6 |

Also taken from its list of what was checked: the residuals it names (io_uring, files in flight, loop
devices and swap files, an AppArmor refusal), what a change of the compiler or the source costs the
owner, and the removal of the temporary folder at the end of the install.

Three things in this revision were not measured, and 7.1 marks each: the two unit files as written,
the capability arriving inside the unit, and the task entries read with the capability. The installed
row of AC6 is where each is proved.

### 14.7 The validation of section 0 and of 7.1's second revision (design-veldo-nowork-0344r2-validation-2026-11-14.md)

Verdict CHANGES: three blocking findings and five smaller required changes, all taken. It found the
seven points of 14.6 resolved, and it found that VELDO-0299's AC1 needs no edit and must not get one.
Each finding was a change of text; no part of the design was redone.

| Point | Checked | Where it is fixed |
| :- | :- | :- |
| N1 batch clones and candidate workspaces still declared and adopted as scratch | True in the four places named: section 3's Landing line, three rows of 6.10 and two rows of 8.8. Of the two kinds offered, the agent repository kind is taken, with a form on the item, because one kind gives a clone every rule an agent repository has. One thing the validation did not raise: the agent repository's row does nothing at run finished, the event a clone's teardown and a batch's discard send, so the table gains a row chosen by the form. The look now starts at the item's own folder | 0.1, section 2, section 3, 4.1 (form), section 5 (the row and "Which kind a private repository is"), 6.1 (declare), 6.10, section 7 (the look), 8.8; ticket 0302 AC1, ticket 0315 AC1 with the row for an adopted batch clone, ticket 0347 AC3 and AC5 |
| N2.1 a failed snapshot write is in no criterion | True. The failures are listed, and each refuses the removal | 0.3 ("A save that fails"), 0.6, 0.7 (the Snapshot store shape, the mutation); ticket 0345 AC5, ticket 0348 AC1 and AC3 |
| N2.2 a second snapshot for one item, and a crash between the save and the removal | True: the first form had one folder per item and said nothing of a retry. One numbered folder per attempt, never replaced or deleted; the keep record names the one used; a retry uses it only when it still equals the item | 0.2 (three rows of the crash table), 0.3 ("One folder per attempt", "A retry is idempotent"), 4.1, 6.1 (keep), 8.8; ticket 0345 AC5, ticket 0315 AC2, ticket 0348 AC2 |
| N2.3 changed after the snapshot, for the two removals with no owner | True: only Discard had the second look. Review scratch and a worker clone are compared file by file just before each delete | 0.3, 6.5 (two rows), section 7; ticket 0336 AC3, ticket 0347 AC3, ticket 0348 AC2 |
| N2.4 review scratch without a snapshot is caught by nothing | True | Ticket 0336 AC3 (a falsifier), ticket 0348 AC3 (a mutation) |
| N2.5 Save and ignored files that are work | True: Save could never finish, or would lose a file written after its snapshot. Before Save's remove the ignored files that are work must equal the snapshot, and rule 5's case 3 counts exactly those as saved | 0.3, 6.5, section 7 (rule 5, the Save row); ticket 0318 AC2 |
| N3.1 a restore can come back incomplete and say success | True. Whether there is a snapshot is read from the keep record; a missing folder or manifest, another digest and a path that leads outside the target are refusals | 0.5, 0.6, 6.1 (restore); ticket 0346 AC2 |
| N3.2 an agent that deletes the store or a kept ref | True: scripts/veldo-guard.sh inspects only push and the landing commands. (a) named in 0.9; (b) reconcile, veldo space kept and restore check every keep record and report what is missing, and the report stays. (c), the guard hook that refuses a command naming the store or the kept refs, was recommended and not required. It is not taken here and is put to the lead in section 15 | 0.3 ("The store is watched"), 0.9, 6.6, 8.8, section 10; ticket 0346 AC1 and AC5 |
| N-R1 an agent worktree's kept refs written into the agent repository | True. The first way offered is taken: they are fetched into the shared repository and written there | Section 0 (the terms), 0.2, 6.5, section 7; ticket 0345 AC1, and the shape in 0.7 |
| N-R2 the clean clone lets two kinds of work through | True for both. Log commits are read. A local remote is read for the commits; a remote on another host is a stated residual | 0.1, 0.9; ticket 0347 AC2 |
| N-R3 shapes the suite does not plant | Taken, all five, with the adopted batch clone of N1 | 0.7; ticket 0348 AC1, AC2 and AC3 |
| N-R4 the writer check: process id reuse, and a reader gone before the probe looks | True for both. SO_PASSPIDFD was measured on this host before it was written in: each part carries a pidfd of its writer, and it reads as ended for a writer that has gone. The reader waits with one read on descriptor 1 after its end line. The /proc residual is named, and the reader checks that /proc is a process file system | 7.1 ("Who is on the other end", the reader's bullets, check 5 and 6, "What stays unread"); ticket 0344 AC1 and AC5 |
| N-R5 git's replace refs, and where H is read | True: git show honours a replace ref. The line uses cat-file under --no-replace-objects with the commit's full hash, and the setup text says H is copied from the approved review record | 7.1 (the install lines); ticket 0344 AC7 |

Also taken from its table of the previous points: one more falsifier for the capability attribute's
version (0344 AC1), and the reader's run time recorded by the installed row (0344 AC6).

Not taken, because the validation listed it under what is sound: a keep step retried after the
item's HEAD has moved finds its head ref at another commit and stays deferred as keep_failed. That
loses nothing. Kept refs numbered per attempt, as snapshots now are, would end the deferral, and that
is a later change if the lead wants it.

Two things in this amendment were not measured. That a rename onto an existing non-empty folder
fails is how the rename call is defined, and ticket 0345's retry row is where it is shown. The
reader's blocking read after its end line was not run inside the unit; the installed row of 0344 AC6
is where it is proved.

### 14.8 The final check of section 0 and of 7.1 (design-veldo-nowork-r2-validation-2026-11-14.md)

Verdict CHANGES. It found every point of 14.7 and of 14.6 resolved and the lead's answers taken as
given. It found again that VELDO-0299's AC1 needs no edit and must not get one, and that text is not
edited. It found two new defects, one in each addition of the sixth amendment. Both are taken, and
both were changes of text.

| Point | Checked | Where it is fixed |
| :- | :- | :- |
| F1 a retry's snapshot replaces the record of an earlier attempt whose files were already deleted | True. The record held one snapshot and a later save wrote it again, so after a review scratch removal that stopped at its second file, the retry's snapshot was the only one a restore applied. The record now lists every attempt and a later write removes none, also a write that saves nothing. Restore applies every listed attempt, the oldest first, and refuses when any is missing or not whole. The listing and the watch check every listed attempt. Drop lists every attempt folder of the item, the ones no record lists included | 0.2 (one row), 0.3, 0.5, 0.6, 0.7, 4.1, 6.1, 6.6, 8.8; ticket 0345 AC5, ticket 0346 AC1, AC2, AC3 and AC5, ticket 0315 AC2, ticket 0348 AC3 |
| F2 a writer that writes first and then executes the reader | True by the kernel's definition of execve. It was not run on this host; ticket 0344's row shows it. Closed as the check says: the probe requires NoNewPrivs 1 and Seccomp 2 of the writer, the reader writes its header only after it has locked itself, and it writes the table only after the probe's byte. The writer check stays | 7.1 ("A writer that becomes the reader", the reader's bullets, the header line, check 5); ticket 0344 AC1 |

The seventh amendment took F1 and F2 only, because the lead's brief for it named those two. It left
out F3, where the folder remover leaves a worker clone's folder when the comparison with the
manifest stops it, and two points of F4, the gap between the last look and git's one remove command
in Discard and in Save, and the wording of the second History entry of VELDO-0299. F4's other
point, that drop takes the attempt folders no record lists, went in with F1.

The eighth amendment takes them, by the lead's word that both are required under the owner's rule,
F4 included. The check listed F4 as recommended and offered a second way for its first point, to
name the gap as a residual in 0.9. That way is not taken: the gap is closed.

| Point | Checked | Where it is fixed |
| :- | :- | :- |
| F3 a stop by the manifest comparison leaves the folder under its marked name | True. 6.5 renamed the folder back only when the second probe found a user, and 8.8 marks an item gone when nothing is at its locator. The first way the check offered is taken: on that stop the remover renames the folder back to its locator before it defers the item. Reconcile also looks for the marked name before it marks anything gone | 0.2 (one row), 0.3, 0.6, 0.7, 6.5, 8.8; ticket 0347 AC3, ticket 0315 AC2, ticket 0348 AC2 and AC3 |
| F4 a file written between the last look and git's one remove command, in Discard and in Save | True. The worktree is moved to a marked name with git's worktree move, and the in-use probe and the look at the worktree are made again under that name. A crash in between is set right with git's worktree repair at reconcile. What stays outside is one sentence in 0.9: a process that finds the marked name | 0.2 (one row), 0.3, 0.6, 0.7, 0.9, 6.5, section 7, 8.8; ticket 0318 AC2 and AC3, ticket 0315 AC2, ticket 0348 AC2 and AC3 |
| F4 attempt folders no record names can only grow | Drop has listed and taken them since the seventh amendment. The listing now shows each under its item, so none grows unseen | 0.3, 0.5; ticket 0346 AC3 and AC5 |
| F4 the wording of VELDO-0299's second History entry on AC1 | Taken as the check words it: a new History line says AC1 is read more strictly. The criterion's text and the earlier entry are not edited | VELDO-0299, History |

That git refuses to move a locked worktree and one that holds a submodule is how git documents the
command. It was not run on this host for this amendment; ticket 0318's rows show it.

## 15. Open questions for the lead

None is open.

The one question the validation of section 0 left (14.7, N3.2) was whether the guard hook should
refuse a shell command that names the snapshot store or the kept refs. The lead answered on
2026-11-13: take it, as one small ticket after 0346. It is VELDO-0349; section 13 records the
decision and 0.3 holds the rule.

The six points this section put about section 0, and the one about 7.1 (one capability or two), were
answered by the lead on 2026-11-13. Section 13 records each answer with its reason, and sections 0 and
7.1 carry them.
