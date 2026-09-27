---
schema: veldo.spec/v1
id: VELDO-0169
title: Every path that hands out work refuses a unit of a stopped project, and a claim on a unit with no project, as the Gate refuses them
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W129
plan_revision: 4
depends_on: [VELDO-0031, VELDO-0064, VELDO-0075, VELDO-0076]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "engine/.veldo/control_andon*.py"
  - ".veldo/control_andon*.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0169_*.py"
  - "scripts/suites/60_veldo_0064_inbox.py"
  - "scripts/suites/71_veldo_0076_projects.py"
  - "scripts/suites/72_veldo_0075_andon.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0169-stopped-project-checks-where-work-is-taken.md"
  - "specs/index.md"
  - "proof/VELDO-0169/*"
behavior_bearing: true
observability:
  logs: >
    Record each refused resume or claim with the unit, its project, the refusal the Gate's project check
    named, and the record versions it was decided from.
  metrics: >
    Count resumes and claims refused by reason (project_not_active:<state>, owner_not_current,
    missing_authority:project).
  traces: >
    Join each refusal to the assignment, stop or claim command and the project record version it read.
  error_taxonomy: >
    The refusals are the Gate's own names, unchanged: project_not_active:PAUSED, :CANCELED, :COMPLETED,
    :owner_not_current, :not_a_project and missing_authority:project; a pause committed after the check
    and before the write refuses as stale_version.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Resuming a parked unit through its assignment (VELDO-0064) refuses a unit whose project is
      stopped. Set and completeness: control_assignment's resume asks the shared Gate's project check
      (control_eligibility.Gate.project_problems) for the parked unit before it writes the new claim, and
      pins the project and owner records that check read with the transaction's other inputs, as the claim
      receiver does since VELDO-0076's fix. Drive the resume with the project paused, canceled, completed,
      with its owner not current, and with a pause committed between the check and the write: each is
      refused by the Gate's name, the last as stale_version, and no claim is written. Falsifier: Drop the
      project check from the resume, and the paused-project resume row must fail.
    falsified_by: >
      Drop the project check from the resume, and the paused-project resume row must fail.
  - id: AC2
    text: >
      Claim: Resuming a unit from an andon stop (VELDO-0075) refuses a unit whose project is stopped. Set
      and completeness: control_andon's resume asks the same project check before it issues the fresh
      station contract and pins what it read the same way. Drive it over the same five project states as
      AC1: each is refused by the Gate's name, the stop stays stopped and no contract is issued. Falsifier:
      Drop the project check from the andon resume, and the paused-project andon row must fail.
    falsified_by: >
      Drop the project check from the andon resume, and the paused-project andon row must fail.
  - id: AC3
    text: >
      Claim: The claim receiver refuses a claim on a unit that names no project, as every station refuses
      that unit. Set and completeness: The receiver (control_claim) runs the Gate's project check for
      every claim, not only for a unit whose project field is set, so a unit with no project is refused
      missing_authority:project with nothing written, exactly as the Gate refuses it at a station. The
      suite drives a claim on a unit with no project field, one whose project is null, and one with an
      active project, which is accepted. Falsifier: Skip the check when the unit's project is null, as
      today, and the no-project claim row must fail.
    falsified_by: >
      Skip the check when the unit's project is null, as today, and the no-project claim row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert to the earlier resume and claim paths; the Gate still refuses a stopped project's run at its
  next station, so no stopped project's work is built either way. No automatic rollback is authorized.
---

## Intent

When the owner pauses or cancels a project, no path hands out its work again, not only the paths that
run it.

## Context

W129 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4. The Codex
whole-project review of 2026-09-26 found that a signed claim took a unit of a paused or canceled project,
and the fix landed on main at a4769f68: the claim receiver now asks the Gate's own project check. Its
review (rvfix0926) found the same gap in two more places that hand out work: the assignment resume of
VELDO-0064 writes a fresh claim for a parked unit, and the andon resume of VELDO-0075 issues a fresh
station contract, and neither reads the project's state. The Gate still blocks the run at its next
station, so nothing is built, but the work is handed out and its holder waits on a stopped project. The
same review found the receiver accepts a claim on a unit with no project, which the Gate refuses at every
station (missing_authority:project). This new specification is draft; authoring it supplies neither
implementation proof nor operational activation.

## Out of scope

The Gate's project check itself (VELDO-0076, unchanged); the pause and cancel commands; what becomes of a
stopped project's parked work (VELDO-0133); handing a project to a new owner (Release 3).

## What the reviewer judges

- Normal use: the owner pauses or cancels a project while some of its units are parked on an assignment
  or held at an andon stop, then someone answers the assignment or the stop; a worker claims a unit.
- Threat model: work of a stopped project handed out by a resume or a claim; a pause committed between
  the check and the write missed; a unit with no project claimed. The owner's account, the store and the
  Gate are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store; a project record of another kind planted at the project's id (already refused by the
  Gate as not_a_project).

## Notes

Use the one check. The Gate's project_problems already returns the versions it read so a caller can pin
them, and the claim receiver shows the pattern; a second copy of the rule is the defect this closes.

## History

2026-09-27: new draft from the review rvfix0926 of the Codex-review fixes landed at a4769f68 (items g and
h of its filed list). A draft: only the owner marks a specification ready.
