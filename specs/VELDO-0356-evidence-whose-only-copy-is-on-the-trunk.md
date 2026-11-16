---
schema: veldo.spec/v1
id: VELDO-0356
title: "Evidence whose only copy is on the trunk"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0312, VELDO-0315, VELDO-0323, VELDO-0347]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_space_worker.py"
  - ".veldo/control_space_worker.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/.veldo/control_space_spool.py"
  - ".veldo/control_space_spool.py"
  - "scripts/suites/*_veldo_0356_*.py"
  - "scripts/suites/149_veldo_0312_ticket_ended.py"
  - "scripts/suites/153_veldo_0323_hook_events.py"
  - "scripts/suites/156_veldo_0315_reconcile.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0356-evidence-whose-only-copy-is-on-the-trunk.md"
  - "specs/index.md"
  - "proof/VELDO-0356/**"
behavior_bearing: true
observability:
  logs: >
    A removed evidence file names where its copy was found: the store, a kept ref, or the trunk with the
    commit. A file that stays names why: no land entry declares a trunk for its repository, the trunk
    could not be read, or the trunk does not reach a commit that holds it.
  error_taxonomy: >
    None of its own. The evidence remover's answers are VELDO-0347's.
acceptance_criteria:
  - id: AC1
    text: >
      At ticket ended and project ended, an evidence file whose only copy is a file in a commit the
      declared trunk reaches is removed, when the event is carried by the service, by the space worker,
      or by reconcile completing a past event. Each of the three hands Signal the same trunk function
    falsified_by: >
      Each of these turns a row of its own red, one row per caller. Hand Signal no trunk from that
      caller: the row's file, whose copy is only in a trunk commit, is still there after the event
  - id: AC2
    text: >
      The trunk is the one the work configuration's land entry declares, read through the function the
      space authority already uses for it (control_space_spool.Local.trunk), so a trunk is read in one
      place. The repository's git setting veldo.space.trunk, which is the hook's word, is never read for
      it, and no trunk is guessed. A repository the land entry does not name has no trunk, and its
      evidence is removed only on a copy in the store or on a kept ref, as before
    falsified_by: >
      Each of these turns a row of its own red. Take the repository's default branch when none is
      declared: the row's file has its only copy on that branch and is gone. Read veldo.space.trunk: the
      row sets it to a branch the land entry does not name, the file's only copy is on that branch, and
      the file is gone
  - id: AC3
    text: >
      The trunk is the one declared for that repository: by its path, or by the project its item's scope
      names. A plain repository the land entry does not name has no trunk, even when a bound project's
      trunk has the same branch name
    falsified_by: >
      Answer the first declared trunk for any repository: the row's plain repository with no land entry
      has a branch named as the bound project's trunk, its file's only copy is on that branch, and the
      file is gone
required_evidence: [unit, integration]
rollback: >
  Revert the change. Evidence whose only copy is on the trunk is kept again, as after VELDO-0347. No
  work is lost either way.
---

## Intent

An evidence file may be removed at a ticket's or a project's end once a copy of it is held elsewhere.
The usual place for that copy is the landed commit on the trunk. Today no caller tells Signal which
branch the trunk is, so those files are never removed and the space is never freed.

## Context

VELDO-0347 AC4 kept this on the safe side. Its History (fix round 2, "Trunk-only evidence"): "No caller
of Signal passes the declared trunk (control_space_worker.py, control_service.py, dispatch.py,
control_space_reconcile.py and scripts/gate_space.py, all outside the footprint), so a file whose only
copy is in a commit of the trunk is KEPT." The independent review (review-veldo-0347.md, AC4) reads it
the same way: "A space shortfall, no loss; the caller wiring is a follow-up for the lead."

The remover's side is built and tested. control_space_signal.signal and the evidence remover take
trunk(repository); rows ac4/held-files-go, ac4/unreadable-is-no-copy and ac4/trunk-never-guessed of
suite 150_veldo_0347_unseen_work prove them. This ticket changes neither module.

## Design

The design is docs/design/VELDO-0295-design.md, section 0.4: the remover "removes the file only when
the store holds a blob with that digest, or a commit that the trunk or a kept ref reaches holds a file
with it".

One trunk function. Signal takes trunk(repository). The space authority already answers the declared
trunk of a repository from the work configuration's land entry (control_space_spool.Local.trunk, given
control_service.landing_names), and its docstring says that is the only place a trunk is read from. The
git setting veldo.space.trunk is what the hook reads to decide what to report; the authority never
trusts it, and a removal must not either. So trunk(repository) is that same lookup, with the scope
found from the declarations for that repository, and nothing new reads a trunk. The mapping that
control_space_reconcile.bootstrap returns is handed to Signal by name; trunk is a parameter Signal
already has, so it is added there, and the service, the dispositions task and dispatch.py pass it on
unchanged. Reconcile and the space worker, wherever they build Signal's arguments themselves, take the
same function.

Two callers of Signal are left out, and why. scripts/gate_space.py is a protected path and does not
need the trunk: the gate's helper signs as space-runner, which signals only run finished and verdict
recorded for its own gate, and evidence ends at a ticket's or a project's end. dispatch.py is given the
service's arguments and changes with them.

Rows this ticket changes: none. No row of suites 149, 153 or 156 reads an evidence file. Those three
suites are in the footprint for the new row each caller gets, as VELDO-0347's History asks ("with a row
of its own in the caller's suite"). The 0347 rows that prove the remover's side (ac4/held-files-go,
ac4/unreadable-is-no-copy, ac4/trunk-never-guessed) stay as written.

No protected path is touched.

Footprint. The service, the space worker, reconcile (with bootstrap) and the spool's authority, each
with its synced copy; the ticket's suite, proof and spec; and the three caller suites.
control_space_config.py is not in it: the trunk is not one of the space declarations.

## History

- 2026-11-16: drafted from VELDO-0347's follow-ups and its independent review. Not filed. The number
  was checked free on every ref of the repository.
- 2026-11-16: reviewed. The draft read a plain repository's trunk from veldo.space.trunk, which the
  spool's authority treats as the hook's word and never trusts; the trunk now comes only from the land
  entry, through the function that already reads it, so control_space_spool.py replaces
  control_space_config.py in the footprint. Old AC3 restated the remover's resolution of the trunk,
  which VELDO-0347 built and proves; the new AC3 checks that a repository gets its own trunk and no
  other.
