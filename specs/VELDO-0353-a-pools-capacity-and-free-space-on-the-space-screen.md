---
schema: veldo.spec/v1
id: VELDO-0353
title: "A pool's capacity and free space on the Space screen"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0315, VELDO-0316, VELDO-0319]
placement: [engine, loop]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/.veldo/control_api_models.py"
  - ".veldo/control_api_models.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "engine/ui/src/api/reads.ts"
  - "engine/ui/src/features/space/**"
  - "engine/ui/docs/views/space.md"
  - "engine/ui/e2e/**"
  - "scripts/suites/*_veldo_0353_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/gate_unconfined.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0353-a-pools-capacity-and-free-space-on-the-space-screen.md"
  - "specs/index.md"
  - "proof/VELDO-0353/**"
behavior_bearing: true
observability:
  logs: >
    Each reconcile record names, per pool, the capacity and free space it read, or that it could not
    read them. The read writes nothing.
  error_taxonomy: >
    None of its own. A reconcile measurement that is not a whole number of bytes, or names a pool the
    installation does not have, is refused with the reconcile command, as invalid_input.
acceptance_criteria:
  - id: AC1
    text: >
      Each reconcile records, per filesystem pool, the pool's capacity and free space as it read them,
      on its own reconcile record and in its own command. An engine image pool, for which reconcile has
      no reader, is recorded as not measured. Nothing measures on a timer and no other writer changes
    falsified_by: >
      Each of these turns a row of its own red. Leave the figures off the record: the row runs reconcile
      and the read has no capacity. Measure on an interval: the row that stops the fixture clock sees a
      new figure with no reconcile
  - id: AC2
    text: >
      space.pools gives each pool its capacity from the newest reconcile record, and its free space from
      the newest of three records that already hold one: that reconcile record, the newest removal on
      the pool (its free space after, VELDO-0300), and the newest judged hold on the pool (the free in
      its reason, VELDO-0316). Each figure comes with the event and the time it was taken at. The read
      measures nothing, scans no journal, and a pool that was never measured says so and shows no number
    falsified_by: >
      Each of these turns a row of its own red. Take free space from the reconcile record only: the row
      removes an item after a reconcile and reads the older figure. Read the filesystem in the read: the
      row's records hold figures the test host does not have, and the read returns the host's. Show a
      pool that was never measured as zero free: the row's new pool reads 0
  - id: AC3
    text: >
      The Pools section shows capacity, free, floor and held for each pool, and beside capacity and free
      the event and the time each was taken at. The row updates from the record stream without a reload.
      An engine image pool's row says its figures are not measured, and keeps the note that removal
      there does not grow the host's free space
    falsified_by: >
      Work free out in the browser as capacity less the usage table's total; the row whose pool also
      holds files Veldo did not make shows a figure that is not the recorded one and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The Pools section shows floor and held, and free space only on a judged hold, as
  before. Reconcile records keep their figures and nothing reads them.
---

## Intent

The owner looks at the Space screen to see how full each pool is. Today a pool's row shows its floor
and what is held on it, and free space appears only on a waiting run. This ticket puts capacity and
free space on the pool's row, each with when it was taken.

## Context

Found by the independent review of VELDO-0319 (review-veldo-0319.md, the not-built list): "No ledger
record holds capacity or current free, and design 6.6 (all from ledger records) contradicts its own
space.pools row. This is a design gap with no owner."

Free space is already recorded in two places: on a removed item (pool_free_before and pool_free_after,
which the remover reads and Signal writes) and on a waiting or advised hold (the free in its reason,
which admission reads). Reconcile writes only its counts on its record. Capacity is recorded nowhere.

## Design

The design is docs/design/VELDO-0295-design.md. Sections this ticket builds: 6.6 (the space.pools row)
and 10 (the Pools row).

The figures stay where they are taken. The service's free-space reader is built in
control_space_reconcile.bootstrap with statvfs on a path of the pool's device. The Reconciler reads,
for each filesystem pool, the free space through that reader and the capacity with the same lookup, and
hands both to Ledger.reconcile, which writes them on the reconcile record in the same command. The
capacity reader is not added to the mapping bootstrap returns: that mapping's keys are handed to Signal
by name, and Signal takes no capacity argument. The new argument is a
keyword with a default (nothing measured), so the callers that pass four arguments today keep working:
suites 132 (ac4/rebuilt-pools-holds), 133, 150_veldo_0317 and 150_veldo_0334, and VELDO-0352's change
to the same command. The pool record is not written: a removal or a hold judgment that wrote it would
add the pool record to every such command, and removals on one pool would then contend for one record.

Admission, the removers, Signal, scripts/gate_space.py (protected) and the CLI's run wrapper (bin/veldo)
are not changed. Admission and the removers read free space through the readers their callers hand
them, and those readers give no capacity. Row compat/one-shot-adapter of 150_veldo_0334 pins the
signature of the admission adapter, and rows ac4/folder-figures and ac4/engine-image-pool of
138_veldo_0300 count the free-space reads; none of them changes.

The read. space.pools takes the newest reconcile record, the newest removal per pool and the newest
judged hold per pool through indexes the Ledger installs when it opens, as VELDO-0319's fix round did
for removals. The removal's place in time is the removal stamp that fix round writes; an older removal
with no stamp is not used for the free figure. Holds are already in the read.

"Free" is therefore "free at the last event that measured it". The screen says which event and when,
because a figure with no age reads as live. Anything written to the disk by something outside Veldo
shows at the next removal, judged hold or reconcile, and the owner's Reconcile button measures on demand.

Rows this ticket changes: none. 150_veldo_0319_space_screen ac4/pools-numbers reads a pool's floor and
held by key and stays as written. No row compares a whole reconcile record or a whole pool record. The
teeth cases of finding 319 anchored in the pools view (space319-held-counts-a-waiting-hold and
space319-advised-holds-not-listed in control_api_models.py) keep their anchors; one whose line this
change moves is re-anchored on the same code with the same target row, and the teeth of finding 319 are
run.

The browser rows live in a spec file of their own, engine/ui/e2e/space-pools.spec.ts, run by this
ticket's own UI suite, and not in e2e/space.spec.ts (row ui/api-only of 150_veldo_0319_space_ui).

Protected path. That suite needs system Chrome, so it needs an entry in scripts/gate_unconfined.json,
which is protected: the owner approves the entry at landing.

Footprint. The Ledger (the reconcile record's figures and the indexes), reconcile, the read model and,
if the view needs records the read model does not hand it today, the authority's read, each with its
copy; the Pools section's files, its page and its browser tests; and the ticket's suites, proof and spec.
No route and no command is added.

For the lead: the review's minor finding M2 (a member with a narrow scope sees a pool's held as the sum
of the holds they may see) is a different concern and is not in this ticket. An engine image pool's
capacity needs an engine reader that reconcile does not have; that is not in this ticket either.

## History

- 2026-11-16: drafted from the review of VELDO-0319. Not filed. The number was checked free on every
  ref of the repository.
- 2026-11-16: reviewed. The draft wrote the figures on the pool record from admission, the removers and
  reconcile. Admission and the removers read free space through readers their callers pass, among them
  scripts/gate_space.py (protected) and bin/veldo, which give no capacity, and row compat/one-shot-adapter
  pins admission's adapter signature; Signal, not the remover, writes the outcome. The ticket now
  records capacity and free at reconcile only and reads free from the records that already hold it. The
  suites named only by kind were looked for: no row compares a whole record, so 150_0316, 138_0300,
  156_0315 and 150_0319 left the footprint. The browser rows get a spec file of their own.
