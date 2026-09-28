---
schema: veldo.spec/v1
id: VELDO-0085
title: Decomposition and concurrent elaboration publication
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W70
plan_revision: 4
depends_on: [VELDO-0037, VELDO-0078, VELDO-0079]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/claim.py"
  - ".veldo/claim.py"
  - "packs/*/.veldo/claim.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_decomposition*.py"
  - ".veldo/control_decomposition*.py"
  - "packs/*/.veldo/control_decomposition*.py"
  - "engine/.veldo/control_alias*.py"
  - ".veldo/control_alias*.py"
  - "packs/*/.veldo/control_alias*.py"
  - "engine/.veldo/control_document*.py"
  - ".veldo/control_document*.py"
  - "packs/*/.veldo/control_document*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0085_*.py"
  - "scripts/suites/59_veldo_0037_aliases.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0085-decomposition-concurrent-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0085/*"
  - "engine/.veldo/control_backlog.py"
  - ".veldo/control_backlog.py"
  - "packs/*/.veldo/control_backlog.py"
  - "engine/.veldo/control_eligibility.py"
  - ".veldo/control_eligibility.py"
  - "packs/*/.veldo/control_eligibility.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/drive.py"
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
      Claim: Decomposition binds one primary specification revision and one admitted backlog item
      per unit. Set and completeness: Enumerate required unit fields, invoke claim.unit_id_problem
      before artifacts and reject invalid IDs, duplicate active spec revisions or authority combined
      across backlog items. New units need fresh priority. Falsifier: Reserve an artifact before
      unit-ID validation; the invalid-ID-no-artifact check must fail.
    falsified_by: >
      Reserve an artifact before unit-ID validation; the invalid-ID-no-artifact check must fail.
  - id: AC2
    text: >
      Claim: Each accepted decomposition artifact uses authority allocation and its source
      revision/role. Set and completeness: Publish identical and distinct source tuples through 0037
      in real SQLite; compare alias reuse, unique distinct aliases and exact source-to-spec mapping,
      preserving existing WARP and VELDO identities. Falsifier: Allocate the alias from checkout
      maximum; the authority-counter comparison must fail.
    falsified_by: >
      Allocate the alias from checkout maximum; the authority-counter comparison must fail.
  - id: AC3
    text: >
      Claim: Published specifications have the accepted complete bytes and declared dependencies.
      Set and completeness: Read the materialized files in another process and compare versions,
      digests, unit ownership and dependency edges; a stale edit or unpublished document cannot
      become admitted execution input. Falsifier: Omit a generated dependency when publishing its
      spec; the decomposition-to-eligibility comparison must fail.
    falsified_by: >
      Omit a generated dependency when publishing its spec; the decomposition-to-eligibility
      comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Decomposition and concurrent elaboration publication. Deliver the normal function needed by the running factory journey.

## Context

W70 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

In normal use, a signed decomposition publishes complete specifications for one
backlog item's proposed units. Authority allocation preserves source identity and historical
aliases. Each unit has one current specification: accepting a new source revision supersedes
the earlier specification in the same authority transaction, including when publishers race.
Dependencies resolve to current unit specifications, and preparation refuses a specification
whose declared dependency aliases disagree with those current specifications. Ordinary
backlog refusals return named outcomes with observations and counts by reason.

The threat model includes invalid unit fields, scope and ownership conflicts, repeated unit
IDs, stale or unpublished bytes, competing source revisions, and dependency bindings that
became obsolete between publication and preparation. The reviewer judges real authority
transactions, materialized bytes and the production admission and eligibility paths using
the declared criteria and their driven negative controls.

Recovery after interrupted publication, broader concurrent-author matrices, extra channel
activation and the filed integration limitations in History remain out of scope. These
checks confer no independent review, human approval or landing authority.

## Notes

0037 owns the only alias counter and source mapping. This consumer publishes the PM
decomposition as actual specifications, with dependencies delivered to 0052 (0092's typed
proposal groups are Release 2 since PLAN-0019 revision 4). Preserve
contract-named scope and one owning backlog item per unit.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 multi-
clone/concurrent-author and AC3 crash/snapshot recovery matrices moved to Release 2. Approved
decomposition and actual specification/dependency publication remain. The criteria, declared
evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.

2026-09-25, PLAN-0019 revision 4 review: the Notes no longer name VELDO-0092 as a consumer of the
published decomposition's dependencies, since revision 4 moved it to Release 2; the PM's proposals take
effect one owning command at a time (VELDO-0088). Notes only: criteria and status are unchanged.

2026-09-27, build: publish a signed decomposition proposal through
`control_decomposition.py`, using VELDO-0037's authority counter, source tuple and exact
materializer. Its alias renderer binds the document's ID to the authority allocation,
including on retry and reuse. The required unit fields are unit, scope, requirements,
eligible holders, source, role, front matter, body and dependencies. Published entries
carry their alias, revision, digest, source, role, path, unit and owning backlog item.
The backlog binds these accepted revisions when preparing or appending units, checks
them again at admission and prioritization, and passes their dependencies to eligibility.
The shared eligibility service refuses stale or unpublished specification input. Existing
file-only specifications keep their prior admission path and historical identities.

The footprint gains `control_backlog.py` and `control_eligibility.py` with their copies:
AC1 needs the real unit writer's ownership binding and AC3 needs the real consumer's
publication and dependency checks. It also gains the mutation registry and
`scripts/drive.py` for the required falsifiers and assertion red record. Both new
modules are scaffolded; every changed engine module has an identical installed copy.
Suite `82_veldo_0085_decomposition` and proof in `proof/VELDO-0085/` cover the three
criteria. Status stays ready; no independent approval, merge or full gate is claimed.

2026-09-27, review fixes: publication reuses the passed backlog service's module and refusal
class, returning and observing all ordinary refusals with counts by reason. The allocator
supersedes earlier specifications for the same unit in its authority transaction; concurrent
allocations serialize through its counter and compare-and-swap retry. Dependency publication
resolves only the current specification, and the production unit validator refuses obsolete
dependency aliases as `binding_mismatch:dependency_specification` during prepare. Four new
rows cover the refusal paths, twin specifications, stale dependency preparation and two
concurrent publications. Four unique finding 85 mutations exercise these checks. The reviewer
judgment section adds normal use, threat model and scope prose; criteria text is unchanged.

Filed for later, not fixed here: decomposition is not yet wired to Telegram or the API;
a dependency on a prepared unit in another item is accepted; a Gate with no workspace refuses
every bound unit as `stale_subject:specification_bytes`; eligibility reads the binding from
the live connection rather than its snapshot; the same unit ID in two items is refused only
at prepare. These remain outside this review-fix scope.

The alias regression fixture now installs the binding reader and document parser consumed
by allocation, so its isolated module directory exercises the complete production dependency set.

Review-fix verification: all twelve decomposition rows pass, all sixteen finding 85
mutations fail their named rows by assertion, and both red records are regenerated.
The alias and backlog regression suites pass. Git boundary checking reports no violations;
all 233 engine pairs are byte-identical; repository validation passes. The whole selftest
completed once with no failing row. `proof/VELDO-0085/review-checks.json` and its logs retain
the exact results. No repository gate, independent approval or push is claimed.

2026-09-27, blocking review fix: the allocator transaction refuses superseding prepared or admitted units as `invalid_transition:supersede_prepared_unit`, other owning items as `binding_mismatch:supersede_other_item`, and another specification role as `binding_mismatch:supersede_role`; ordinary republication before prepare still supersedes. Three assertion rows and three globally unique finding 85 mutations cover these checks, and the concurrency row now uses two processes. This resolves the earlier same-unit cross-item publication limitation. Filed, not fixed: admission does not recheck a dependency superseded from another item after prepare, and `unit_heads` scans every accepted head per lookup.
