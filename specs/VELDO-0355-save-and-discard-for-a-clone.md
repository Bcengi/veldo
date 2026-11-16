---
schema: veldo.spec/v1
id: VELDO-0355
title: "Save and Discard for a clone"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0318, VELDO-0327, VELDO-0343, VELDO-0345, VELDO-0347]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_request_settlement.py"
  - ".veldo/control_request_settlement.py"
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_keep.py"
  - ".veldo/control_space_keep.py"
  - "scripts/suites/*_veldo_0355_*.py"
  - "scripts/suites/150_veldo_0347_unseen_work.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0355-save-and-discard-for-a-clone.md"
  - "specs/index.md"
  - "proof/VELDO-0355/**"
behavior_bearing: true
observability:
  logs: >
    A Save names the commit it made and the kept ref that holds it. A Discard names the snapshot it saved
    and the kept refs. A refusal names the file or the commit that differs from what the owner was shown.
  error_taxonomy: >
    space_disposition_choice for a Save or Discard of a clone whose table has no clone row or whose
    request did not offer it; space_deferred:remove_refused when the clone's files or its head differ
    from the request; space_deferred:keep_failed when the snapshot or a kept ref cannot be written or
    read back, or a file changed after the snapshot.
acceptance_criteria:
  - id: AC1
    text: >
      A request for a batch clone or a candidate workspace offers Save, Keep and Discard. Its signed
      terms name the clone as a clone, with its path, its form, the files in no commit and the commit it
      was at, and say what each answer does: where Save puts the files, that Discard saves them first
      and keeps every commit, and the restore command with the item filled in. A request raised with
      Keep alone stays as it was shown, and only Keep is taken for it
    falsified_by: >
      Each of these turns a row of its own red. Present the clone with a worktree's terms: the row reads
      the signed content and finds no clone line. Offer the new answers on a request raised before this
      change: the row's open Keep-only request shows Save and Discard after a restart
  - id: AC2
    text: >
      Save commits exactly the files the owner was shown, in the clone, on a new branch from the commit
      shown. The keep step then records that commit and every other commit of the clone on kept refs of
      the main repository and reads each back, and only then the clone is removed. When the files or the
      commit differ from the request, compared with what the keep step saved and never with an earlier
      look, nothing is removed and the item is deferred
    falsified_by: >
      Each of these turns a row of its own red. Remove the clone after the commit without the keep step:
      the row's saved commit is in no repository. Compare before the snapshot: the row writes a file
      between the look and the snapshot, and a file the owner never saw is committed
  - id: AC3
    text: >
      Discard saves the clone's work tree in the snapshot store and reads it back, keeps every commit as
      Save does, compares each file with the manifest immediately before it is deleted, and removes the
      git folder last. When a comparison stops the removal the folder is renamed back to its locator
      before the item is deferred. Restore brings back what was discarded
    falsified_by: >
      Each of these turns a row of its own red. Remove without the snapshot: the row's uncommitted file
      is neither in place nor restored. Leave the folder under its marked name at a stop: the row runs
      reconcile and finds the item marked gone
  - id: AC4
    text: >
      The Ledger takes a settled Save or Discard for a clone only when the item's own table has the
      clone's row and the request offered that answer. A Save or Discard planted for a request that
      offered Keep alone, or for a clone declared under table 1, is refused space_disposition_choice
      with nothing written. A worker clone of a run that has ended still raises no request. Worktree and
      review group requests are unchanged
    falsified_by: >
      Each of these turns a row of its own red. Take any choice the settled effect holds: the row plants
      a settled Discard for a request that offered Keep alone and the clone is made due. Read the offer
      and not the table: the row plants a settled Discard for a table 1 clone and the clone is made due
required_evidence: [unit, integration]
rollback: >
  Revert the change. A clone's request offers Keep alone again, and a clone with files in no commit
  stays, deferred, as after VELDO-0347. Nothing a Save or a Discard kept is removed by the revert.
---

## Intent

A batch clone or a candidate workspace with files in no commit raises a request, and the only answer
the owner can give is Keep. So such a clone can never be removed, however the owner answers. This
ticket gives the request its other two answers and the remover that carries them, with the same
guarantee a worktree has: nothing is deleted before it is saved.

## Context

VELDO-0347 left this open by decision (its History, decision 3 and the first follow-up): "No criterion
asks for a remover that carries a Save or a Discard of a private repository, so a clone's request
offers Keep and nothing else". The independent review of VELDO-0347 (review-veldo-0347.md, question 3
and finding 3) confirmed the three guards that hold it: the presentation offers "accept keep" only,
settlement refuses a choice the receipt does not list, and the Ledger refuses any other settled choice
for a clone (control_space.py, _disposition_change).

## Design

The design is docs/design/VELDO-0295-design.md. Sections this ticket builds: 0.3 (only the owner's
Discard, and Discard saves first), 0.2 (commits on a kept ref before anything is removed), 0.5
(getting it back) and 6.5 (removers), each for a private repository where VELDO-0318 and VELDO-0343
built them for a worktree.

Terms (control_request_settlement.py). A clone's terms gain the commit the clone was at and the two
new answers. They are still a clone's terms: the field clones and no worktrees, one clone. The
Keep-only form stays valid for requests already open, and settlement keeps refusing a choice the
receipt does not list.

The remover (control_space_remove.py). The disposition remover reads a clone's terms as well as a
worktree's. Save and Discard for a clone reuse what exists: the keeper's snapshot of a private
repository's work tree (VELDO-0345), the per-file comparison and the rename back that VELDO-0347 built
for a worker clone, and the comparison with what was saved that VELDO-0318's fix round built for a
worktree. Save's branch takes the next free name, so two clones of one ticket do not collide (the
defect the review of VELDO-0318 found for worktrees, finding 4).

The Ledger (control_space.py). The guard that refused every choice but Keep for a clone now reads the
request: an answer the request offered, for an item whose own table names the clone's row.

Rows this ticket changes, all of scripts/suites/150_veldo_0347_unseen_work.py:
- ac3/clone-request. It pins the clone's terms as exactly {keep, clones: [{item, path, form, files}]}, the
  choices as ["accept keep"] and no Discard in the brief. It now pins the new terms (the commit the clone
  was at and the three answers) and keeps its other checks.
- ac3/ledger-keep-only. It plants a settled Discard and a settled Save of a clone whose request offered
  Keep alone and expects space_disposition_choice. After this change a new clone request offers three
  answers, so the row's fixture writes its request in the Keep-only form, as a request left open from
  before the change, and expects the same refusal. Save and Discard of a three-answer request are the
  rows of AC2 and AC3.
- The teeth case space347-ledger-applies-any-settled-choice-to-a-clone (control_space.py) is anchored on
  the line this ticket replaces, "if record['kind'] != 'worktree' and choice != 'keep':". It is
  re-anchored on the new guard, still targets ac3/ledger-keep-only, and gains AC4's row.

Rows that stay as written, checked on 837fa81a: ac3/table-1-clone and ac3/table-2-clone read the clone
items of the request and not its choices; 142_veldo_0303_space_paths ac4/candidate-with-work-stays reads
the clone's item and files by key; no row of 150_veldo_0327_disposition names a clone. Those two suites
are not in the footprint. The teeth cases of findings 327, 340, 342 and 347 anchored in
control_request_settlement.py, control_space.py and control_space_remove.py keep their anchors; one whose
line this change moves is re-anchored on the same code with the same target row, and the teeth of those
findings are run.

No protected path is touched.

Footprint. The request terms, the removers, the Ledger, Signal (it hands the remover the answer and
the clone's row), the keeper (only if a clone's snapshot for a Discard needs a field it does not write
today), the ticket's suite, proof and spec, and the suite of the two rows above. The service's
dispositions task already applies any settled Save or Discard whatever the item's kind, so
control_service.py does not change.

For the lead: with no ledger (the standalone remover) there is no snapshot store, so a clone with
uncommitted files still stays there. That is VELDO-0347's third follow-up and is not in this ticket.

## History

- 2026-11-16: drafted from VELDO-0347's follow-ups and its independent review. Not filed. The number
  was checked free on every ref of the repository.
- 2026-11-16: reviewed. The rows named only by kind were looked for: only ac3/clone-request and
  ac3/ledger-keep-only change, so suites 142 and 150_0327 left the footprint. The teeth case on the
  Ledger's clone guard is named. AC1's second falsifier, which tested the Ledger, moved to AC4, and AC1
  gained one for requests already open.
