---
schema: veldo.spec/v1
id: VELDO-0188
title: The running factory starts a Line for a project the moment the store records it, staffed from the project's team or the default team, and stops the Line of a closed project, with no reinstall and no restart
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W148
plan_revision: 4
depends_on: [VELDO-0076, VELDO-0089, VELDO-0143, VELDO-0154, VELDO-0161, VELDO-0162, VELDO-0185]
placement: [loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_team*.py"
  - ".veldo/control_team*.py"
  - "packs/*/.veldo/control_team*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "scripts/suites/*_veldo_0188_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0188-a-line-for-every-project-at-run-time.md"
  - "specs/index.md"
  - "proof/VELDO-0188/*"
behavior_bearing: true
observability:
  logs: >
    Record each Line started, restaged or stopped with its project, execution repository, the project or
    default team revision its roles came from, the receiver configuration it launches through, the pass and
    the journal position that caused it, and each project left without a Line with its named reason; never
    a credential.
  metrics: >
    Count Lines started, restaged and stopped per pass, projects waiting for their receiver configuration,
    and projects refused a Line by reason.
  traces: >
    Join each Line change to the loop pass that made it, the project record version and the team revision
    it read.
  error_taxonomy: >
    Distinguish a project whose execution repository has no receiver configuration yet
    (missing_authority:receiver:<project>, the Line started at the pass after VELDO-0161 adds it), a team
    role the installation cannot dispatch (invalid_input:line:role:<problem>, the same problems
    control_service's work check names), and a project whose team and the default team are both absent
    (missing_authority:team:<project>); each leaves every other Line serving.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The running authority service starts a Line for a project the moment the store records it
      active, at the loop pass that commit wakes, with no reinstall and no restart, and a service started
      later builds the same Lines from the store. Set and completeness: The factory loop's set of Lines is
      read from the store: one Line per project record (VELDO-0076) in state ACTIVE or PAUSED whose
      execution repository is adopted in this domain, each over the receiver configuration the running
      service holds for that repository (VELDO-0161 AC2). At every pass woken by a journal advance
      (VELDO-0154 AC1's `journal` wake) the loop compares that set with its Lines and starts each missing
      one before it offers work; `serve` builds the same set at start. The installed work configuration
      supplies a Line only for a served repository no project record names yet, as VELDO-0154 built it.
      Nothing else changes the set: no timer and no store read outside a woken pass (VELDO-0154 AC4). The
      suite runs the installed service with one project, then activates a second project created through
      VELDO-0143's provisioner and a third adopted through VELDO-0161, and requires each first unit
      dispatched by the same process (identity and start time unchanged, nothing reinstalled), then
      restarts the service and compares its Lines with the ones before. Falsifier: Build the Lines only in
      FactoryLoop's constructor from the work configuration, and the new-project row must fail on the second
      project's unit with no dispatch.
    falsified_by: >
      Build the Lines only in FactoryLoop's constructor from the work configuration, and the new-project row
      must fail on the second project's unit with no dispatch.
  - id: AC2
    text: >
      Claim: A Line's builder and reviewers come from its project's current team revision, or from the
      default team's current revision when the project has none, and a new team revision staffs the next
      dispatch. Set and completeness: The Line's builder is the team's `implementation` role and its
      reviewers the `independent_review` role (control_team REQUIRED_ROLES), each turned into
      control_service's ROLE_FIELDS by the one mapping VELDO-0185 AC1 applies to the default team, shipped
      as one function both use: the role's first worker as identity, the installation's adapter for the
      role's first eligible engine, the role's current capability configuration revision (VELDO-0162 AC1), and
      the seconds and payload VELDO-0185 AC1 writes. A role the installation cannot dispatch leaves that
      project without a Line, refused by name (invalid_input:line:role:<problem>), and every other Line
      serving. When a team revision becomes current (VELDO-0162 AC2 or AC3), the pass its commit wakes
      restages the Line: a run already dispatched keeps the roles it was dispatched with, and the next
      dispatch uses the new ones. The suite activates one project with its own team revision and one with
      none, then saves a second team revision for the first whose builder runs on the other engine. Falsifier:
      Staff every Line from the default team, and the project-team row must fail on the first project's
      builder engine.
    falsified_by: >
      Staff every Line from the default team, and the project-team row must fail on the first project's
      builder engine.
  - id: AC3
    text: >
      Claim: A project that is closed has its Line stopped by the running service: the Line offers nothing
      from the commit that closes it and leaves the loop once its runs have ended, while a paused project
      keeps its Line and every other Line carries on. Set and completeness: Closed means the project record
      reached CANCELED or COMPLETED (control_project's `cancel` and `complete`). At the pass the closing
      commit wakes, the Line offers no station and no re-run, settles each run that ends as VELDO-0154 AC1
      and AC2 settle them (cancel already asks each running dispatch's stop), and is removed from the loop
      at the first pass that finds it with no running launch and no orphan, its account slots free; the
      loop status then no longer lists it. A PAUSED project keeps its Line, because VELDO-0076's Gate refuses
      its units and a resume must need no restart. The suite cancels one project with a build running and
      completes another with none, while a third project's unit is dispatched in the same passes, and then
      counts the loop's Lines. Falsifier: Keep a closed project's Line in the loop, and the removed row must
      fail on the loop status still listing it.
    falsified_by: >
      Keep a closed project's Line in the loop, and the removed row must fail on the loop status still
      listing it.
required_evidence: [unit, integration]
rollback: >
  Build Lines from the installed work configuration alone again while keeping every project record, team
  revision, dispatch record and receiver configuration. No automatic rollback, retry or recovery is
  authorized.
---

## Intent

A project the owner starts from Telegram, from a conversation or by adopting a repository starts taking
work at once, staffed by its own team, and a project he closes stops taking work, all without anyone
reinstalling or restarting the factory.

## Context

W148 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. VELDO-0154, as
built on branch build-veldo-0154, builds class FactoryLoop in `control_service.py` at `serve` from the work
configuration an installation copies (the installer's `work` option), one Line per repository that
configuration names, each holding the VELDO-0039 Runner over the repository's installed launch receiver. A
project created from
Telegram (VELDO-0143, VELDO-0152) or from a conversation (VELDO-0180) is recorded in the store but named
in no work configuration, so it got no Line until the service was reinstalled. The review of the
conversation drafts filed this and the lead ruled it MVP function (2026-09-27). VELDO-0161 AC2 already has
the running service add an adopted repository's receiver configuration; this specification adds its Line.
The Lines follow the store, the one source of the projects and their teams, and change only at a pass a
commit wakes, as the loop already does. A draft: only the owner marks it ready.

## Out of scope

Recovery of a Line whose start fails part way, and scale of many Lines on one service (Release 2); two
open projects on one execution repository; the conversation Line, which is VELDO-0174 AC4's and is
unaffected.

## What the reviewer judges

- Normal use: the owner writes "start a new personal project called tidepool" in Telegram, answers the
  proposal, and tidepool's first unit is built by its team's builder through the running service; later
  he saves a team revision that moves the builder to Codex and the next unit builds on Codex; when he
  cancels an old project its running build is stopped and it takes no more work.
- Threat model: a project recorded but never given a Line; a Line staffed from the wrong team; a closed
  project still offered work or holding account slots; a Line started by polling or by any source but a
  woken pass; one project's broken team stopping every other Line; a restart that loses or changes Lines.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store; files planted in the installed directory.

## Notes

A Line is keyed by its project and runs over the project's execution repository, so the enrolled
workspace's repository, which VELDO-0185's work configuration names, is served from the work
configuration until its project is activated and from the store after. The reset timer and the launch
pipes of VELDO-0154 AC1 cover every Line the loop holds, the new ones included.

## History

2026-09-27: new draft from the review of the conversation drafts, which filed that a new project gets no
Line without a reinstall; the lead ruled it MVP function. Only the owner marks a specification ready.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).
