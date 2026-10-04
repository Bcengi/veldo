---
schema: veldo.spec/v1
id: VELDO-0204
title: The factory provisions the reservation policy of every registered account, every project and every engineering unit through the existing reservation writer, from the project budgets, team role budgets and account records the owner already controls, on setup's own store connection and at each pass of the running service, so work dispatches on a fresh host and keeps dispatching as accounts, projects and units are added, and a subject it cannot provision is refused by name
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W151
plan_revision: 4
depends_on: [VELDO-0036, VELDO-0062, VELDO-0076, VELDO-0089, VELDO-0154, VELDO-0160, VELDO-0162, VELDO-0171]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_reservation_policies.py"
  - ".veldo/control_reservation_policies.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0204_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0204-reservation-policies-from-owner-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0204/*"
behavior_bearing: true
observability:
  logs: >
    Record each provisioning pass with its caller (setup's connection or the service's loop pass) and, for
    each subject, its scope, the source it was derived from (the project, the team and its revision, the
    roles), the caps derived, and its outcome: unchanged, configured with the policy version the writer
    committed, or refused with the refusal and its class; never a key or a credential.
  metrics: >
    Count provisioning passes by caller and outcome, subjects by scope and outcome, and refusals by name.
  traces: >
    Join each configured subject to the journal record the reservation writer committed (its command id)
    and an online pass to the loop pass that ran it.
  error_taxonomy: >
    Distinguish a caller that does not hold the store's lock (missing_authority:not_the_authority,
    control_api_authority's name), an engineering unit whose policy has no source: its project has no
    record, or neither the project's team nor the default team has a head, or the team lacks the build
    or review role or that role's budget (missing_evidence:reservation_source:unit:<unit>, a name this
    specification adds). The reservation writer's own refusals (missing_authority when the provisioning
    principal does not hold reservation_service, missing_usage_controls, invalid_input, a store refusal)
    are passed through unchanged for the subject they refused.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: On a fresh host, provisioning gives every registered account, every project and every
      engineering unit a VELDO-0036 reservation policy derived from configuration the owner already
      controls, and a unit then dispatches with no other policy written. Set and completeness: A new
      module, control_reservation_policies, reads the store on the caller's connection and derives one
      policy per subject. Project: for every project record (control_project, VELDO-0076, any state), its
      signed coordination budget, each VELDO-0036 kind it states (capacity, invocations, wall_seconds, and
      tokens or messages when stated), owner_minutes left out as no reservation kind. Account: for every
      account record (control_accounts, VELDO-0062, any status), capacity, invocations and wall_seconds
      each the sum of that kind over every project record's coordination budget. Engineering unit: for
      every execution_unit record (never a pm_cycle unit, whose policy the PM cycle keeps writing), its
      team is its project's team record at its current revision (control_team read, VELDO-0089), or the
      default team at its head revision when the project has none (VELDO-0162 read_default); its build
      role is the role its team assignment names (VELDO-0089 assign), implementation when it has none, and
      its review role independent_review; its caps are, for each kind both roles' budgets state, the sum
      of the two. Each derived policy is written by Reservations.configure, unchanged, built as
      control_service builds a line's Reservations (this store's domain, a served repository, the service
      principal and its journal signer, service_authority), with command id
      reservation-policy/<scope>/<subject>/<the policy's current version, 0 when absent>. The suite lays a
      host down with VELDO-0139's setup steps, enrolls the `authority` principal with reservation_service
      as VELDO-0185 AC2 does, activates two projects with different signed budgets, saves a default team
      and gives one project its own team, registers three accounts of two engines and admits units in both
      projects, one with a team assignment naming a specialist build role. Rows: derive/values reads each
      stored policy back and requires exactly the caps above per scope; fresh/dispatch then submits a unit
      through a control_service Line's Runner and account pool, with no configure call of the suite's own,
      and requires the worker slot reserved on a registered account. Falsifier: Leave the account scope
      out of the provisioning pass, and the fresh/dispatch row must fail on no_account with
      missing_ceiling:account among the passed-over reasons.
    falsified_by: >
      Leave the account scope out of the provisioning pass, and the fresh/dispatch row must fail on
      no_account with missing_ceiling:account among the passed-over reasons.
  - id: AC2
    text: >
      Claim: Provisioning reconciles: a policy that already matches its source is left alone, a changed
      source updates the policy through the writer, and nothing is provisioned for an account that is not
      registered or a unit that does not exist. Set and completeness: A stored policy matches when its
      caps equal the derived caps exactly, the same kinds with the same values; its windows (VELDO-0036's
      window action) are not compared, and configure keeps them. A matching subject sends no command. A
      subject with a stored policy and no source record (no account, project or execution_unit record of
      that id) is left as it is: nothing deletes a policy. Subjects are reconciled independently, so one
      subject's refusal leaves every other subject's outcome as it would be. Rows: rerun/unchanged runs
      provisioning a second time and requires every subject unchanged and the journal head unchanged;
      source/project activates a third project and requires every account policy updated to the new sums
      and the existing project and unit policies unchanged; source/team amends one project's team with a
      larger implementation budget and requires that project's unit policies updated and the other
      project's unchanged, then saves a new default team revision and requires only the units of the
      project without a team updated; source/account and source/unit register a fourth account and admit
      a new unit and require exactly their policies added; source/windows reports a subscription window on
      an account, changes the project budgets that account's caps derive from and requires the window
      kept after the update; source/absent requires no policy for an account id with no account record
      and for a unit id with no execution_unit record,
      and the PM cycle's own unit policy unchanged. Falsifier: Configure every subject on every pass
      without comparing its stored caps, and the rerun/unchanged row must fail on the changed journal
      head.
    falsified_by: >
      Configure every subject on every pass without comparing its stored caps, and the rerun/unchanged row
      must fail on the changed journal head.
  - id: AC3
    text: >
      Claim: Provisioning obeys VELDO-0171's lock rule: it runs only on the connection of the store's lock
      holder, offline on setup's own connection when no service runs and inside the running service when
      it does, which provisions accounts, projects and units added while it runs before it offers them
      work. Set and completeness: control_reservation_policies takes the caller's lock descriptor and
      refuses first, writing nothing, unless control_api_authority's authority_problem finds it holds
      authority.lock beside the store its connection opened, and the Reservations it writes through uses
      that exact connection (missing_authority:not_the_authority). Offline, a caller holding the lock
      (VELDO-0185's setup after control_factory_setup take_lock; the suite here) calls the module on its
      own connection. Online, control_service's FactoryLoop runs provisioning with the service's lock on
      the service's connection at its start and at the beginning of every loop pass, before any line runs,
      through its first line's Reservations made current by that line's activate; the pass report carries
      the provisioning outcome, and a provisioning fault is a pass fault by name, never the loop's end. No
      service command route is added: what a running service provisions it provisions itself. The module
      is an installed runtime asset (init_scaffold). Rows: lock/second-connection calls provisioning on a
      second connection while the service fixture holds the lock and requires not_the_authority with the
      journal head unchanged; service/added registers an account and admits a unit through the running
      service after its start and requires both policies committed by the service at the next pass and the
      unit dispatched at that pass on the new account; service/rerun requires a pass with nothing added to
      send no reservation command. Falsifier: Run provisioning only at the service's start, and the
      service/added row must fail on the unit refused missing_ceiling:unit.
    falsified_by: >
      Run provisioning only at the service's start, and the service/added row must fail on the unit
      refused missing_ceiling:unit.
  - id: AC4
    text: >
      Claim: Provisioning is no second writer and no relaxation: every policy goes through
      Reservations.configure, VELDO-0036's missing_ceiling checks stay as they are, and a subject that
      cannot be provisioned is refused by name and observed. Set and completeness: A unit whose project has
      no project record, whose project has no team and no default team head exists, or whose team lacks its
      build or review role or that role's budget, gets no policy and is refused
      missing_evidence:reservation_source:unit:<unit>; a writer refusal is answered and observed by its own
      name for its subject, never as unknown_outcome. Each refusal appears in the provisioning answer and
      in the log with its subject, scope and class. Rows: refuse/missing-source admits a unit whose
      project's team was never saved on a store with no default team and requires the named refusal, no
      unit policy, and that unit's dispatch then refused missing_ceiling:unit while the other units
      dispatch; refuse/principal runs provisioning as a principal without reservation_service and requires
      every subject refused missing_authority by the writer with nothing written; census/writer requires
      the canonical production callers of Reservations.configure to be control_reservation_policies and
      control_workflow_cycle_pm and no production code to write a subscription_reservation policy entity
      any other way; the rows of VELDO-0036, VELDO-0154 and VELDO-0160 stay green. Falsifier: Provision a
      unit with no source from its project's coordination budget instead of refusing it, and the
      refuse/missing-source row must fail on a configured unit policy.
    falsified_by: >
      Provision a unit with no source from its project's coordination budget instead of refusing it, and
      the refuse/missing-source row must fail on a configured unit policy.
required_evidence: [unit, integration]
rollback: >
  Remove control_reservation_policies and the loop's provisioning call; the policies already written stay
  as accepted records and dispatch keeps working on them, while accounts, projects and units added later
  again need a policy written by hand. No automatic rollback is authorized.
---

## Intent

The owner sets up a factory on a fresh host, logs in each account, and work dispatches: every account,
project and unit has the reservation ceiling VELDO-0036 requires, taken from the budgets the owner already
signed, and an account registered, a project activated or a unit admitted later is covered at the
next pass with nothing done by hand.

## Context

W151 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5, ahead of W145.
VELDO-0185 is blocked a third time (proof/VELDO-0185/README.md on build-veldo-0185c, a3c3940d): a pooled
reservation (control_reservations reserve_pooled, VELDO-0160) needs an account, a project and a unit
policy, each with capacity, invocations and wall_seconds, and refuses missing_ceiling:<scope> without
one; the only production writer is Reservations.configure, and its only production caller is the PM
cycle's own unit policy. Account registration, project activation and the team writers store their
budgets but write no policy, and suite 83's fixture constructor writes the policies the factory loop
needs. This specification adds the missing provisioning and nothing else; VELDO-0185 AC4's dispatch
consumes it, its setup calling the module on its own connection after AC2's reservation_service
enrollment of the `authority` principal.

## Out of scope

Setup's step that calls the module (VELDO-0185); deleting or retiring a policy; a per-account lifetime
allowance of the owner's own (see Notes); the PM cycle's unit policies, which it keeps writing; the
subscription windows (VELDO-0036's window action, VELDO-0062); any change to Reservations, its checks or
its refusal names; a service command route for reservation configuration.

## What the reviewer judges

- Normal use: setup provisions every account, project and unit on its own connection, the owner starts
  the service, and the first unit dispatches; later the owner registers an account, activates a project,
  amends a team or admits a unit, and the next loop pass writes exactly the policies that changed, while a pass
  with nothing changed writes nothing.
- Threat model: a ceiling taken from a number no owner set, or larger than the budget it derives from; a
  second policy writer or a policy entity written around the writer; a missing source answered with a
  default ceiling, or a missing_ceiling check bypassed; a policy for an account that is not registered or
  a unit that does not exist; a source change that never reaches its policy, or a re-run that rewrites
  matching policies; a subscription window lost on update; a store written by a process that does not
  hold its lock; a refusal that leaves no observation.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as a source
  changed between the pass's read and its commit (the lock leaves one writer, and the next pass
  reconciles); forged rows in our own store.

## Notes

Where each value comes from. A project's ceiling is its coordination budget, which control_project
already names as the reservation service's units and which the owner signs at activation; no command
changes it afterwards. A unit's ceiling is the sum of the budgets of the two roles that dispatch it, from
the team the Line itself reads for those dispatches (control_workflow_cycle_pm engineering_role), just as
the PM cycle takes its unit policy from its role's budget; a unit that reworks or takes several reviews
draws on that one sum and is refused usage_cap:unit when it is spent, and the owner raises the role
budgets in the role form, which the next pass carries into the policy. Engine qualification data
(VELDO-0127, VELDO-0160) is not used: it records engine facts shipped with a release, such as the
windows an engine reports, not owner configuration.

The gap. No owner-controlled value states a lifetime allowance for an account, and VELDO-0036 requires
one. An owner limits an account by its registered concurrency, enforced by the account pool (VELDO-0160),
by its status, and by its provider's windows, enforced from what the engine reports (VELDO-0036,
VELDO-0062). The account policy is therefore the sum of every project's coordination budget: every charge
on an account is charged on a project in the same reservation, so that sum is the most the projects can
put on it, and the account adds no limit of its own and no invented number. It is not the concurrency:
a slot freed by release_account (VELDO-0154) still counts toward the account's capacity balance, so a
capacity equal to the concurrency would close the account the pool has reopened. Because project budgets
never change after activation, account sums only grow as projects are added. Should the owner want a
per-account allowance of their own, it is a later owner-signed revision through VELDO-0203's path; this
specification creates no configuration for it.

The command id names the policy's current version, so a re-run after a crash finds the policy already
matching, and a source that changes and changes back is written again rather than answered as a replay of
the earlier command.

## History

2026-10-04: new specification for the third VELDO-0185 blocker, recorded on build-veldo-0185c at
a3c3940d, written and marked ready at the owner's request; VELDO-0185 now depends on it.
