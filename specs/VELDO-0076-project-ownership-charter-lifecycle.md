---
schema: veldo.spec/v1
id: VELDO-0076
title: Project ownership, charter, lifecycle, and transfers
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W61
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0036, VELDO-0068, VELDO-0073]
placement: [contracts, engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_eligibility.py"
  - ".veldo/control_eligibility.py"
  - "packs/*/.veldo/control_eligibility.py"
  - "engine/.veldo/control_project*.py"
  - ".veldo/control_project*.py"
  - "packs/*/.veldo/control_project*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0076_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0076-project-ownership-charter-lifecycle.md"
  - "specs/index.md"
  - "proof/VELDO-0076/*"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Project activation binds owner, charter, execution repository, authority policy and
      finite coordination budget. Set and completeness: Enumerate those required schema fields and
      omit each in a real signed activation command; valid current owner acceptance creates one
      active project, while missing authority or budget refuses. Falsifier: Skip the budget
      predicate; the unbounded-project check must fail.
    falsified_by: >
      Skip the budget predicate; the unbounded-project check must fail.
  - id: AC2
    text: >
      Claim: Pause and cancellation stop new assignments and dispatch while preserving accepted
      history. Set and completeness: Activate, pause and cancel a real project with pending and
      running work; observe the ordinary host stop policy, no new dispatch and unchanged landed
      receipts. Falsifier: Permit frontier to assign work after pause; the paused-project check must
      fail.
    falsified_by: >
      Permit frontier to assign work after pause; the paused-project check must fail.
  - id: AC3
    text: >
      Claim: Project completion requires terminal objectives and disposition of its ordinary
      outstanding obligations. Set and completeness: Attempt completion with an open objective,
      assignment, decision, dispatch or reservation separately, then with all required records
      resolved; compare accepted project state and preserved history. Falsifier: Complete with a
      pending objective; the incomplete-project refusal check must fail.
    falsified_by: >
      Complete with a pending objective; the incomplete-project refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Project ownership, charter, lifecycle, and transfers. Deliver the normal function needed by the running factory journey.

## Context

W61 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: the enrolled owner activates a project with a real signed command that binds its owner,
  charter, one execution repository, authority policy and a finite coordination budget; exactly one
  active project results. Pausing or canceling it stops new assignments and dispatch (the frontier
  offers nothing from it, running work follows the ordinary host stop policy) while accepted history
  and landed receipts stay as they were. Completing it is accepted only when every objective is
  terminal and its ordinary outstanding obligations (assignments, decisions, dispatches,
  reservations) are resolved.
- Threat model: an activation missing any bound field, or with no finite budget, accepted; an
  activation by someone who is not the current enrolled owner; the frontier assigning or a dispatch
  starting from a paused or canceled project; a pause or cancel rewriting accepted history or
  receipts; completion accepted with an open objective, assignment, decision, dispatch or
  reservation. The owner's account, the store and the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); additional
  owners, transfers and delegation (Release 3); recovery and restart (Release 2); forged rows in our
  own store and files planted in the installed directory.

## Notes

Release 1 establishes the enrolled owner, one execution repository, charter and bounded
project coordination. The roster does not grant admission authority. Additional owners and
transfer require the Release 3 governance work rather than a default inferred delegation.

A unit's project is judged only from a record of kind `project` at `project:<name>`; a record of
any other kind there is refused by name (`project_not_active:not_a_project`), and the project
service owns the `project:` id prefix as well as the kind, so no other command writes at a
project's id. Only the recorded owner may pause, cancel or complete a project, so a project whose
recorded owner is no longer a current person member holding `project_owner` in its scope (demoted,
out of scope, revoked or expired) could be stopped by nobody. It fails safe the way VELDO-0138's
demoted owner does: the Gate refuses its units (`project_not_active:owner_not_current`) and its
work halts at its next station until the owner is current again. Handover to a new owner is
Release 3.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 multi-owner
transfer and unused AC2 release-execution depth moved to Release 3; AC1 concurrent activation
and AC2 restart moved to Release 2; multiple-channel breadth moved to Release 4. Owner,
charter, budget, pause and cancellation remain. The criteria, declared evidence universe,
Context and Notes above now carry only the retained function. No specification status or
historical proof was changed.

2026-09-25, build: the footprint gains `control_eligibility.py` (engine, installed and pack copies). Pause and cancel must stop dispatch as well as the frontier's offers, and the one place every station (selection, claim, the runner's preparation, the receiver's recheck, publication) asks is the VELDO-0052 Gate, so its unit check now refuses a unit whose project is not ACTIVE (`project_not_active:<state>`); a check in frontier.py alone would have left every dispatch path open. The project service is the new `control_project.py`; the frontier, `request.py` and `authorization.py` are unchanged. Status unchanged.

2026-09-25, review fixes: the Gate judges a unit's project only from a record of kind `project`
(a record of another kind at the project's id refuses `project_not_active:not_a_project`) and the
project service owns the `project:` id prefix through `declare_owners`, since a signed generic
upsert of another kind at `project:X` got X's units past the Gate and blocked X's activation; an
ACTIVE project whose recorded owner is not current halts at the Gate
(`project_not_active:owner_not_current`), the fail-safe of VELDO-0138's demoted owner, with
handover left to Release 3. Rows `project/foreign-kind`, `project/owner-demoted` and
`project/owner-revoked`, red at 93a56d6 by assertion; five finding 76 mutations. Status unchanged.

2026-09-25, review 2 (filed item fixed): the scope and person parts of the owner-currency rule were never driven (a mutant dropping either survived). The owner-demoted row now drives both; mutations owner-scope-unchecked and owner-person-unchecked red it (finding 76: 23).
