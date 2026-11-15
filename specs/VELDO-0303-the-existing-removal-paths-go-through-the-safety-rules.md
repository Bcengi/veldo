---
schema: veldo.spec/v1
id: VELDO-0303
title: "The existing removal paths go through the safety rules"
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
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "engine/.veldo/control_clone.py"
  - ".veldo/control_clone.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_launch_work.py"
  - ".veldo/control_launch_work.py"
  - "engine/.veldo/control_space_standalone.py"
  - ".veldo/control_space_standalone.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/66_veldo_0042_clones.py"
  - "scripts/suites/128_veldo_0235_land_locally.py"
  - "specs/VELDO-0308-run-finished-from-the-receiver.md"
  - "scripts/suites/*_veldo_0303_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0303-the-existing-removal-paths-go-through-the-safety-rules.md"
  - "specs/index.md"
  - "proof/VELDO-0303/**"
behavior_bearing: true
observability:
  logs: >
    Each of these removals is an outcome record like any other. A refusal that was swallowed before is a
    deferral with its rule's name.
  error_taxonomy: >
    clone_in_use is unchanged and stays first. Every other refusal is space_deferred with the rule's name.
acceptance_criteria:
  - id: AC1
    text: >
      A fleet worktree is removed through Signal without git's force option; one with an untracked file
      stays, and the refusal is a deferral on the record
    falsified_by: >
      Leave the force option in place; the row's untracked file is lost and the row fails
  - id: AC2
    text: >
      A clone's teardown and its failed-provision cleanup go through Signal; the clone_in_use refusal is
      unchanged; the pins are released after the removal outcome
    falsified_by: >
      Leave the direct delete in place; the row with a process holding an open file in the work tree finds
      the folder gone and fails
  - id: AC3
    text: >
      A run directory is removed through Signal, both at the receiver's end and for a leftover the sweep
      finds
    falsified_by: >
      Leave either direct delete in place; the item stays present after its folder is gone and the row
      fails
  - id: AC4
    text: >
      The landing line's candidate folders and the lander's candidate workspace are removed through Signal
    falsified_by: >
      Leave the direct delete in place; the same row for a candidate item fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The seven paths delete directly again, the fleet's with git's force option.
---

## Intent

Seven places in the engine delete a folder or a worktree directly today, one with git's force option and
several with errors swallowed. This ticket sends each of them through Signal, so the safety rules apply
and a refusal is a deferral on the record.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.10 (existing removal paths: the
first seven rows of the Replaced table). Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Fleet worktrees, Clone provisioner, Receiver, Landing line. The first seven rows of the table
> of 6.10 are the list; the batch and sandbox rows are VELDO-0324.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. A clone and a candidate workspace are private repositories: VELDO-0347 AC3
  has the keep step record their commits in the main repository before the folder goes, and defers one
  whose work tree holds uncommitted work.
- 2026-11-14: built. No acceptance criterion changed. What the build decided, recorded here because
  the criteria do not say it:
  - The seam. Each of the five modules is given `space`, a mapping with the Ledger and the arguments
    Signal takes (probe, kinds, remover, free, keep, owner_live and the rest), or None. Each module
    carries the same small function, space_signal: it finds the live items the ledger records at or
    beneath the paths of the removal, signals the event once for each owner among them with every
    part of that owner as the subject, and answers with the state of each path's item. It deletes
    nothing. The function is carried five times because no shared module is in this footprint.
    Nothing in the engine builds `space` yet: the service holds no Ledger, and the creators declare
    nothing until VELDO-0302. Until both are wired the five paths run as before.
  - With no ledger each path removes as it did, as a creator with no central installation creates as
    it did (design 6.1). So the direct deletes are still in the files, in the branch that runs only
    when `space` is None; the existing suites of the clone, the run directory and the landing line
    drive that branch and are unchanged. The boundary check of VELDO-0304 has to name those branches.
    One thing differs with no ledger: the fleet never passes git's force option. It runs git's
    non-forced remove, and only for a worktree this provisioner added whose checked-out commit has
    not moved since, because with no ledger there is no keep step and a commit made on the detached
    head would be named by nothing. Anything else stays and is listed, never swallowed.
  - The events. A fleet worktree: worktree abandoned. A clone at teardown and at a failed
    provisioning, a run directory at the receiver's end and at the sweep, a candidate folder at the
    landing line's close and the lander's candidate workspace at discard: run finished. Design
    section 5 names run finished for a worker clone and leaves the landing line's event unnamed; the
    lander's discard is the sibling of the batch's discard, which 6.10 gives run finished.
  - A private repository is not removed at run finished by today's table. The row of an agent
    repository whose form is a worker clone or a candidate workspace is VELDO-0347. Until it is built
    the ledger does not make a clone's work tree or a candidate folder due at run finished: it stays,
    it holds its root, its pins stay held, and the teardown is refused. The suite adds that one cell
    to a copy of the registry, as a stand-in.
  - Rule 3. Where a module has just read from the kernel that the run is over (the clone's users
    have ended, the sweep's kernel test, a receiver whose group is known to be empty or whose engine
    never started), rule 3 is answered conclusive for the runs that own the items of that removal,
    and for no other owner. A receiver whose group nobody could read does not answer; the wired
    answer does.
  - The pins. They are released only when the work tree's item is removed or gone, or when no live
    item records the work tree and the kernel says nothing is at its path. Not found is the only
    answer that counts: a path that could not be read releases nothing.
  - A failed provisioning confirms the items still in state declared, so that the event reaches
    them, and then signals. What was never made is marked gone by Signal.
  - The fleet signals only for its own worktree: when the worktree's owner also owns another
    worktree or agent repository the event would end, nothing is signalled and the worktree stays.
  - A refusal is space_deferred and the rule's name. For an item no rule deferred it is the state the
    item is in: due (report mode), removing (left under its marked name), kept, present; and
    not_in_ledger when no item records the thing. space_deferred is in the clone's taxonomy as
    stale_subject, beside clone_in_use.
  - For the lead, not built here because control_retirement.py is not in this footprint: a clone
    whose teardown is refused keeps its dispatch's worker slot, since the clone obligation stays open
    while its root is on disk or a pin is held. In report mode every clone is left due, so once a
    ledger is wired every dispatch would keep its slot until the owner's Confirm. The same holds for
    a clone a rule defers. This needs a decision before `space` is wired into the clone provisioner.
- 2026-11-14: fixed from the review (verdict FIX, five findings), by the lead's decisions. No
  acceptance criterion changed. The footprint gained the files named below.
  - Withdrawn, from the entry above: "With no ledger each path removes as it did" and the fleet's
    rule "only for a worktree this provisioner added whose checked-out commit has not moved since".
    The review reproduced losses in that branch, which is the only branch any installation runs
    today: git's non-forced worktree remove took an ignored local file and a repository in an
    ignored folder with its only commit, and a commit made and reset away was left named by
    nothing; and the clone's teardown deleted the commits and files of a build whose result was
    refused. The owner's rule holds with a ledger or without one.
  - Finding 2 and the review's table of direct deletes. With no ledger every one of these paths now
    looks first and deletes only what the look answers for: the fleet's worktree remove, the
    clone's teardown and failed-provision cleanup, the receiver's and the sweep's run directory
    removal, the landing line's close and the lander's discard. The look is one new module,
    control_space_standalone.py, which runs the unique work probe (VELDO-0299), the removers' own
    reading of ignored files that are work, the probe for repositories beneath the thing, and the
    keep step (VELDO-0345) with no ledger: the kept refs in the main repository are the record. A
    worktree or a private repository whose work tree holds anything in no commit stays (with no
    ledger there is no Discard and no request). So does anything with a git repository beneath it,
    a private repository with linked worktrees, a thing whose main repository cannot be named, and
    anything the look could not read. A folder (a run directory, a clone's root, an observation
    folder) goes only when it is no repository and holds none. What stays is named where each
    module already names a refusal: the fleet's answer and deferred list, the clone's retire event
    and its Refused (space_deferred and the rule), the runner's observations, the receiver's
    run_removal, the runtime's kept list, the candidate's space entry. The main repository of a
    clone is the repository the store binds for its domain and repository; of a candidate folder,
    the runtime's root; of a candidate workspace, the lander's repository.
  - What that costs, for the lead. A worker clone whose work tree holds an untracked or modified
    file is no longer deleted when its users end. The clone obligation of its retirement stays
    open, so its dispatch keeps its worker slot until the file is committed or taken away. That is
    finding 4's case reached without a ledger, and VELDO-0308 AC4 is its fix. Every teardown,
    close and discard also writes kept refs in the main repository, and they are never deleted.
  - Two older rows changed because they stated the old behaviour. 66_veldo_0042
    clone/retire-after-users-end and clone/retire-waits-for-group retired a clone in which the
    worker's probe had left an untracked file; the first now also asserts that this teardown is
    refused as space_deferred:unique_work with the pins held, and both take the file away before the
    teardown that removes the clone. 128_veldo_0235 local/lands asserted that the logging git
    shows no fetch; the keep step's fetch from the candidate workspace, a folder on this host, into
    the caller is now told apart and asserted to be the only one. Nothing else in either row moved.
  - Finding 1. The scaffold lays down control_space_signal.py and the look with the modules it
    loads (the probes, the keeper, the removers' readers, the ledger module, the declarations
    reader): the service's closure reads them from the five modules. The ledger module's loader was
    spelled so that the closure's reader can name the files it loads; it loads what it loaded.
  - Finding 3. Before the receiver or the sweep signals run finished for a run directory, the other
    users of the clone that run's dispatch uses are read (clone_users). While one has not ended,
    nothing is signalled: the run directory stays, the refusal is clone_in_use with their names,
    and the sweep comes back. A clone that cannot be read counts as in use.
  - Finding 5. `space` is passed to the three places that build a clone provisioner.
  - Finding 4. Not built here. VELDO-0308 has it as AC4, with the pin rule.
  - Rows added to the suite, each with a registered falsifier: loss/fleet-ignored-file,
    loss/fleet-nested-repository, loss/fleet-reset-commit, loss/clone-refused-build,
    loss/run-directory-repository, loss/candidate-commits, f3/consumer-holds-clone,
    f5/clones-given-space. ac2/no-ledger-as-before is now ac2/no-ledger-clean-clone.
  - Not closed here: between the look and the delete nothing holds the thing, where the wired
    removers move it to a marked name and look once more. The callers have just read that the
    run's processes are gone, and the fleet's worktree is the retiring worker's own.
- 2026-11-14: AC3's sweep behaviour narrowed by VELDO-0308 (the review of that ticket, finding 1,
  and the lead's decision). A sweep is no retry: Runner.clear_runs sends run finished for a
  leftover run directory only while no ending event has reached its item, at most once, and for
  the run directory alone; one the ledger already holds (due, deferred, removing or kept) is
  dropped as handed over and is retried by the ledger's own retries (design section 7, Retry).
  Suite 142 rows ac3/deferred-then-swept and f3/consumer-holds-clone were changed there to say so:
  no second event from the sweep, and the run directory of a run that still has its clone goes
  with the clone's teardown. No acceptance criterion of this ticket changed.
- 2026-11-14: fix, after the review of 66b943b2 (review-veldo-0350-and-suites.md, part B) and the
  lead's decision. The review commit of this ticket (e9e70768) broke suite 67_veldo_0056: with no
  ledger the lander's discard gave every candidate workspace to the keep step, which wrote
  refs/veldo/kept refs into the caller's repository on every land, refused or not, and left a
  candidate stopped in a conflicted merge on disk. VELDO-0056's contract is that a refused land
  leaves the caller as it was and nothing left over. No acceptance criterion of this ticket changed.
  - The lead's decision. A landing candidate holds only commits that can be made again, so it is
    removed with no kept ref written, but only after a check, and it fails closed: a commit that
    nothing else holds is kept on a kept ref as before.
  - The check is control_space_standalone.candidate, reached from the lander as space_rebuildable.
    It writes nothing. The workspace goes with no kept ref only when every commit it names (by its
    HEAD, a ref, a log or an operation head) is reachable from a branch, a tag, a remote-tracking
    ref or a kept ref of the caller's repository, or from the workspace's trunk ref (the trunk as
    the lander fetched it), or is one of the lander's own: a merge or the projection commit the
    candidate's record names, or the one commit the lander had made and not yet recorded, which
    must be the HEAD with exactly the parents the record's next step has. Its work tree must hold
    no ignored file that is work, and what git's status lists must be nothing, or the tracked
    paths of the merge the record's next step is, in progress, or the projected paths while the
    projection is the next step. A stash, a linked worktree, a repository beneath it, another
    operation, a file git does not track beside a merge, or anything git could not read: the
    answer is no state, and the workspace is given to space_standalone exactly as before (kept
    refs, or it stays with space_deferred:unique_work). lander.py and control_space_standalone.py,
    canon and copy.
  - What the lead should know. The lander's own merge and projection commits are reachable from
    no ref of the caller: they are accepted because the record names them and each is made again
    from held parents on every land. Read strictly ("every commit reachable from a kept ref, a
    branch or the trunk"), a built candidate that was refused at the gate would still write kept
    refs and suite 67's rejection row would stay red; this is the reading that makes it green. The
    trunk is taken from the workspace's own trunk ref, not asked of the remote again.
  - Suite 67_veldo_0056 is green again, 11 rows, 37 passed, unchanged. Suite 142 is 33 rows:
    fix/candidate-rebuildable (a built candidate, one stopped in the conflicted merge, one whose
    last merge was not recorded yet: each removed, no ref of the repository written or moved) and
    fix/candidate-fail-closed (a commit the record does not name, a commit on the head with other
    parents than the next step's, a commit only the log names: each on a kept ref, its file read
    from the repository alone; a file git does not track beside the conflict, a merge of another
    commit, a changed tracked file, an ignored file: each workspace stays, byte for byte).
  - Nine falsifiers added under finding 303 (33 now), each applied once and red on its row:
    space303-lander-keeps-every-candidate, space303-lander-removes-a-candidate-without-either-look,
    space303-candidate-fetched-trunk-holds-nothing, space303-candidate-unaccounted-commit-goes,
    space303-candidate-any-head-commit-is-the-landers, space303-candidate-untracked-file-goes,
    space303-candidate-any-merge-is-the-landers, space303-candidate-changed-file-goes,
    space303-candidate-ignored-work-goes. space303-lander-deletes-a-workspace-without-the-look is
    re-anchored, unchanged in meaning (its line moved one level in).
  - One older row changed back. 128_veldo_0235 local/lands asserted, since the review commit, that
    the keep step's fetch from the candidate into the caller is the one fetch of a local land. A
    landed candidate holds nothing the caller's trunk does not, so there is no such fetch and no
    kept ref; the row asserts that.
  - One row of VELDO-0310 changed. 147_veldo_0310 f1/remote-branch-contained read the candidate of
    a remote landing in the project's own repository only because the discard had put it on a kept
    ref there. It is no longer there, so the landed step brings the candidate's objects into the
    project's repository as well as the other one (the path f1/project-repository-brought already
    covers); the row asserts both, and every other check of the suite is unchanged.
- 2026-11-14: fix 2, after the review of 107bcecc (review-veldo-0303fix-0350fix.md, verdict FIX:
  the check answered rebuildable for four workspace states that hold work) and the lead's four
  decisions. Each fails closed: doubt keeps the candidate on a kept ref, as before the fix. No
  acceptance criterion changed. lander.py and control_space_standalone.py, canon and copy.
  - Decision 1 (the review's cases A and D). The exception is gone: a commit is the lander's only
    when the candidate's record names it. A commit on the head with the parents of the record's
    next step (a hand resolution committed in the workspace), or a commit where the projection
    would be, is kept on a kept ref. So that this does not turn a land refused by the read right
    after the lander's own commit into kept refs in the caller (suite 67's row
    candidate/every-git-operation-checked faults every invocation), the lander notes each commit
    its own command made in the record, under made, as that command returns and before anything
    else is read; when the read that names it fails, it is read once more for the record alone and
    the land is refused as the first read said.
  - Decision 2 (case B). When a step stops, the lander records exactly what it left
    (control_space_standalone.left, under left): the commit it was on, the commit being brought
    in, git's status listing, the index entries of the listed paths and the blob id of each listed
    file as it is in the work tree. At the discard a step in progress is the lander's only when a
    second read answers exactly the same. A hand edit to another tracked file, a partial
    resolution inside the conflicted file, a staged resolution, or a record that says nothing: the
    workspace stays.
  - Decision 3 (case C). No ref of the workspace says what is held. The trunk the candidate was
    built on is the commit the record stored (its watermark), and it is a commit like any other:
    held only by what is outside the workspace. Work under a moved trunk ref is kept.
  - Decision 4 (the stale trunk). A commit no ref of the caller holds counts as held only by the
    remote's trunk as the remote says it is now. The lander reads it at the discard with the
    recorded identity (ls-remote, which writes nothing), only when some commit needs it. The
    answer holds what it contains only when that commit is known in the workspace. A remote that
    cannot be read, a rewound one, one that went on to a commit the workspace does not have, or no
    remote: the candidate is kept on kept refs.
  - What the lead should know. (a) Decisions 3 and 4 came out as one rule: what holds commits is
    the caller's refs and the remote's own answer, and neither the workspace's ref nor the record's
    watermark is trusted to hold anything. A record with no watermark (a sync that failed after its
    fetch) is therefore still cleared when the remote holds what was fetched, which suite 67 needs.
    (b) A remote whose trunk advanced to a commit the workspace does not have (another land won
    the race) keeps the candidate on kept refs: nothing is fetched to prove containment. That is
    the fail-closed reading, and it writes kept refs into the caller on such a refused land. (c)
    The discard now makes two invocations of the lander's own (config, ls-remote) after the gate
    when the caller does not hold the trunk. Suite 67's row candidate/every-git-operation-checked
    faults the construction's invocations, those up to the gate, as it did, and asserts that the
    two after it are exactly these.
  - Suite 142 is 37 rows, 63 passed: fix2/unrecorded-commit-kept, fix2/step-in-progress-exact,
    fix2/trunk-from-record and fix2/remote-holds-trunk, each with the review's case as a row that
    keeps the work. The fixture's trunk now comes from a bare remote of its own and a conflicted
    candidate is stopped by the lander's own step. One older check moved: the candidate whose last
    step the record did not name was removed, and is now kept (decision 1). One older check was
    made harder: the step of another commit now carries a matching record of what was left, and
    still stays.
  - Falsifiers under finding 303 are 43, each applied once and red on its row. Added:
    space303-candidate-head-commit-by-its-parents, space303-candidate-noted-commit-not-the-landers,
    space303-candidate-step-in-progress-only-untracked-looked-at,
    space303-candidate-left-files-not-read, space303-lander-records-nothing-at-the-conflict,
    space303-candidate-trunk-read-from-the-workspace, space303-candidate-fetched-trunk-held-unasked,
    space303-candidate-workspace-trunk-held-unasked, space303-lander-gives-the-look-no-remote,
    space303-lander-notes-no-commit-of-its-own (on suite 67). Re-anchored, unchanged in meaning:
    space303-lander-removes-a-candidate-without-either-look,
    space303-candidate-fetched-trunk-holds-nothing, space303-candidate-unaccounted-commit-goes,
    space303-candidate-any-head-commit-is-the-landers, space303-candidate-untracked-file-goes,
    space303-candidate-changed-file-goes.
  - Not done here: the review's suggestion to assert in 128_veldo_0235 local/lands that the caller
    holds the landed tip and passes a connectivity check after the discard.
