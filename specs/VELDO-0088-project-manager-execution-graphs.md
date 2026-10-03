---
schema: veldo.spec/v1
id: VELDO-0088
title: Project-manager execution graphs
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W73
plan_revision: 4
depends_on: [VELDO-0035, VELDO-0043, VELDO-0045, VELDO-0060, VELDO-0061, VELDO-0076, VELDO-0078, VELDO-0079, VELDO-0089, VELDO-0132, VELDO-0151, VELDO-0154]
placement: [contracts, loop, fleet, distribution]
protected_paths: []
footprint:
  - ".veldo/control_factory_setup.py"
  - "engine/.veldo/control_factory_setup.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/control_workflow_cycle*.py"
  - ".veldo/control_workflow_cycle*.py"
  - "packs/*/.veldo/control_workflow_cycle*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_eligibility.py"
  - ".veldo/control_eligibility.py"
  - ".veldo/authority_contract.py"
  - "engine/.veldo/authority_contract.py"
  - ".veldo/control_team.py"
  - "engine/.veldo/control_team.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/33_veldo_0020_authority.py"
  - "scripts/suites/*_veldo_0088_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0088-project-manager-execution-graphs.md"
  - "specs/index.md"
  - "proof/VELDO-0088/*"
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
      Claim: The PM reads an immutable accepted snapshot and returns proposals under its bounded
      coordination contract; its cycles run the default pipeline, and every model-mediated node
      launches as an ordinary worker run through the Runner. Set and completeness: Run actual
      LangGraph proposal, no-action and failure cycles on the one default pipeline workflow revision
      (intake, coordinate, elaborate, admit, assign, build, prove and gate, review, land, report). At
      the coordinate node observe a PM run dispatched through the Runner (VELDO-0039) under a
      coordination station, with the capability configuration the team's PM role names (VELDO-0151)
      and the cycle's accepted snapshot as input, returning one typed proposal document of owner
      questions, decomposition and a staffing choice per unit. Enumerate required
      project/source/watermark/input-version/reservation fields and compare every cycle receipt,
      including empty cycles, to real store records. Falsifier: Invoke the model for a coordinate
      node inside the cycle runner instead of dispatching a run through the Runner; the
      Runner-dispatch check must fail.
    falsified_by: >
      Invoke the model for a coordinate node inside the cycle runner instead of dispatching a run
      through the Runner; the Runner-dispatch check must fail.
  - id: AC2
    text: >
      Claim: Nodes can propose but cannot admit, prioritize, assign, dispatch or complete directly.
      Set and completeness: Compare node/output registrations with typed proposal handlers and
      attempt shell/SQL actions, invented roles and store access from a graph process; observe only
      separately validated commands changing domain state. Waiting on a person releases the worker.
      Falsifier: Let a node set priority directly; the unauthorized-transition check must fail.
    falsified_by: >
      Let a node set priority directly; the unauthorized-transition check must fail.
  - id: AC3
    text: >
      Claim: One cycle per project runs, with one bounded follow-up when relevant input arrives
      during it. Set and completeness: Hold an actual PM cycle while an owner answer and worker
      completion arrive; observe one active cycle, one pending follow-up using the new accepted
      snapshot, and no self-triggered loop after inputs are consumed. Apply the finite cycle budget.
      Falsifier: Discard pending input when the active cycle ends; the expected-follow-up
      observation must fail.
    falsified_by: >
      Discard pending input when the active cycle ends; the expected-follow-up observation must
      fail.
  - id: AC4
    text: >
      Claim: For work the PM judges to be one unit, the one coordination run also writes the
      requirements and stages that unit with the team's four required roles, and the builder fetches
      a referenced ticket itself. Set and completeness: For an admitted objective whose text is
      "please do BCG-123", a one-unit change, run the cycle the factory loop (VELDO-0154 AC1) starts
      for its project. The PM run's proposal judges one
      unit and writes its requirements, carrying the owner's message and every reference in it as he
      wrote it; the elaboration station is recorded as done by that run and no elaboration run is
      dispatched; the unit is staged with the project manager, elaboration, implementation and
      independent review roles through VELDO-0089's assignment, a builder and an independent
      reviewer; and the builder's run fetches BCG-123 itself with the catalog server its role's
      configuration lists. A one-line fix costs one coordination run, one build and one review.
      Falsifier: Dispatch a separate elaboration run for work the PM judged to be one unit; the
      one-run staging row must fail.
    falsified_by: >
      Dispatch a separate elaboration run for work the PM judged to be one unit; the one-run staging
      row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Project-manager execution graphs. Deliver the normal function needed by the running factory journey.

## Context

W73 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5 (moved from stage 4
by revision 4, because the PM role's capability configuration comes from the stage 5 VELDO-0151).
Section 4 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
designs the PM as a role whose reasoning runs as ordinary worker runs. This is the thin VELDO-0088 of
stage 2 of the design's critical path (section 12): one PM run stages one unit with the four required
roles, and the builder fetches the ticket itself. Work of several units, with its separate elaboration
run and second PM cycle, is VELDO-0146, stage 3 of that path.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied. Work the PM
judges to be several units (VELDO-0146) and quoting each reference with its tool, fetch time and
digest (VELDO-0091).

## What the reviewer judges

- Normal use: the factory loop starts a PM cycle for a project with new input; the cycle runs the default
  pipeline revision, dispatches the PM run through the Runner with the role's configuration and the
  accepted snapshot, and applies the returned proposals one owning command at a time; for one-unit
  work that run also writes the requirements and stages the unit with the four required roles, and
  the builder fetches the referenced ticket itself.
- Threat model: a model called inside the cycle runner or the authority instead of as a dispatched run; a
  separate elaboration run or a second cycle spent on one-unit work; a unit staged without one of the
  four required roles; a node
  that admits, prioritizes, assigns, dispatches or completes directly, or reaches the store, a shell
  or SQL; a proposal applied after an earlier one in the same cycle was refused; an empty cycle with
  no receipt; pending input dropped, or a second concurrent cycle for one project. The owner's
  account, the store and the installed runtime are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); persistent checkpoints, retry and replacement-adapter matrices (Release 2); atomic proposal groups
  (VELDO-0092, Release 2); a PM that edits its own team or workflow; forged rows in our own store
  and files planted in the installed directory.

## Notes

Use the actual installed nonpersistent LangGraph step runtime and Veldo-owned workflow
definition. The authority service runs the cycle scheduler: the factory loop inside it (VELDO-0154
AC1) starts a PM cycle for any project with new relevant input, and the cycle runner, on Linux,
executes the bound workflow revision one judged step at a time; PM runs go to whichever host their
role allows. Proposals take effect through their owners: the cycle checks the document's structure
and hands each proposal, in order, to the command that owns it (VELDO-0064 for a decision request,
VELDO-0079 for grooming, VELDO-0085 for publication, VELDO-0089 for an assignment); a refusal stops
the rest of that cycle's proposals by name and is reported, and the next cycle starts from the new
accepted snapshot. All-or-nothing groups are VELDO-0092, in Release 2. A one-line fix costs one
coordination run, one build and one review. Until VELDO-0091 lands, the requirements carry each
reference as the owner wrote it and the builder fetches it with the catalog server its role lists
(VELDO-0127, VELDO-0144); VELDO-0091 then has the coordination run fetch and quote it. This item brings 0093 ordinary cycle scheduling forward: at most one cycle per
project and one bounded follow-up for pending relevant input. Checkpoint recovery and broad
replacement equivalence remain Release 2.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3
retry/cancellation/replacement-adapter matrix moved to Release 2. Actual PM execution remains;
ordinary serialized scheduling and one pending-input follow-up move forward from 0093. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), section 4(e). AC1: cycles
run the default pipeline, model-mediated nodes launch through the Runner as ordinary worker runs,
and one coordination run may also write the requirements for single-unit work; its falsifier is now
the Runner-dispatch check. The Notes say the authority service runs the cycle scheduler and how
proposals take effect through their owning commands now that VELDO-0092 is Release 2. A What the
reviewer judges section is added. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: split on the design's section 12, because a specification ships
whole and the run-check refuses one whose dependencies are not shipped. This specification is the thin
VELDO-0088 of the critical path's stage 2: AC1 keeps the Runner dispatch with its falsifier, and new AC4
is the one-unit path, where the coordination run writes the requirements and stages the unit with the
four required roles and the builder fetches the ticket itself (section 12), with its own falsifier.
Several-unit work moves whole to VELDO-0146. depends_on adds VELDO-0089 (the four required roles),
VELDO-0129 (the factory loop starts the cycle) and VELDO-0151 (the configuration each role names), and
the work item moves to stage 5. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: the factory loop that starts the cycle is VELDO-0154, split
from VELDO-0129 (its former AC4 is VELDO-0154 AC1), so depends_on names VELDO-0154 in place of
VELDO-0129 and the loop references follow. Criterion meaning and status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: the footprint named `control_project_cycle*.py`, which
does not exist; the cycle runner is `.veldo/control_workflow_cycle.py`, so the footprint names
`control_workflow_cycle*.py`. Criteria and status unchanged.

2026-10-02, implementation on build-veldo-0088: the footprint adds the factory
service, dispatch and eligibility modules and their engine copies. AC1 requires
the factory pass to offer a coordination station before an engineering unit
exists; AC3 consumes that same pass. The mutation registry is added for finding
88. Initial cycle and proposal code is being built and is not qualified by this
entry. The specification remains ready.

2026-10-02, integration prerequisite: AC1 uses a genuinely enrolled service with
the Runner reservation guard. That guard already requires `reservation_service`,
but membership rejected that role. The footprint adds the authority contract and
its engine copy to make the existing reservation grant enrollable; no reservation
check is weakened.

2026-10-02, single-unit integration: the footprint adds the team service and its
engine copy, a necessary change to the VELDO-0151 base. Assignment now reads the
risk from a production-published unit's accepted specification when the unit has
no inline risk. The earlier 0151 fixture documented its manual risk decoration;
the PM path must use the real publication instead. Review-policy checks remain
unchanged.

2026-10-02, contract evidence: the authority suite footprint is extended for the
reservation service role now admitted by the real membership writer. Its matrix
still enumerates all seven R37 roles and additionally this existing reservation
service grant. Ten scoped behavior rows pass. This is partial implementation
evidence: the builder catalog fetch, factory-started single-unit journey and
graph-process capability attacks still need direct integration observations.
No landing or completed-criterion claim is made.

2026-10-02, continuation: the factory consumes accepted team assignments for build
and independent review. The footprint adds the launch module and engine copy
because Runner preparation must bind that authority instead of requiring a
legacy claim. Dispatch preparation and acceptance recheck the assignment.
Graph node capability attacks, combined input coalescing and complete receipts
receive direct process observations in the scoped suite.

2026-10-02, one-unit cost observation: successful assigned engineering advances
through the factory without another idle PM run. Completion during an active PM
cycle still joins an owner answer in one follow-up. The suite counts all
dispatch attempts through review launch, so an extra elaboration or coordination
run cannot hide behind the latest-attempt reader.

2026-10-03, independent review follow-up: proposals now name the accepted team's
PM worker, whose membership enrolls the trusted service signing edge key; cycle
receipts remain owned by the distinct service principal. The suite constructs
Service and Line and reaches from_line through Line.run. A refused engineering
adapter is reported per unit, and an exhausted pending follow-up is observed
without aborting the factory pass. Elaboration requires this cycle's successful
publication to name the claimed unit. Five review rows and five finding-88
mutations cover these corrections. The existing footprint covers every file;
no specification status, assignment authorization or protected path changes.

2026-10-03, review evidence: all twenty-one behavior rows pass in the normal and
clean gate environments. The unchanged 1773b279 archive is red by assertion on
all five new review rows; the original 24c0c90b archive is red by assertion on all
twenty-one rows. The review cases use a fresh five-cycle project fixture, keeping
the original sixteen rows and twelve-cycle fixture intact. Mutation execution,
the full gate and the independent landing decision remain reviewer-owned.

2026-10-03, production enrollment follow-up: AC1 and AC4 require the default PM
created by factory setup to sign proposals with the service journal key. Add the
setup module and its engine copy to the footprint because owner-run setup is the
membership enrollment writer; team revisions deliberately cannot grant membership.
A fresh production setup must accept a PM-signed assignment without fixture PM
enrollment. AC3 also requires unexpected start faults to propagate on both the
initial and pending-input paths; only named Refused outcomes are observed locally.
Three finding-88 mutations and three behavior rows cover these corrections.
