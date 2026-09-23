---
schema: veldo.spec/v1
id: VELDO-0043
title: Replaceable LangGraph execution adapter
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W28
plan_revision: 3
depends_on: [VELDO-0035]
placement: [loop, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0043_*.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0043-replaceable-langgraph-adapter.md"
  - "specs/index.md"
  - "proof/VELDO-0043/*"
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
      Claim: Actual LangGraph exchanges plain versioned lifecycle data through a replaceable adapter
      interface. Set and completeness: Enumerate start, advance, suspend, cancel and
      proposal/failure interface operations; execute each using the installed LangGraph runtime and
      accepted snapshots/supplied results. A deterministic interface stub may check shapes, not
      replace actual runtime evidence. Falsifier: Return a LangGraph-specific object in the domain
      response; the plain-data interface check must fail.
    falsified_by: >
      Return a LangGraph-specific object in the domain response; the plain-data interface check must
      fail.
  - id: AC2
    text: >
      Claim: Graph execution cannot confer domain authority. Set and completeness: Exercise nodes
      returning admission, priority and completion assertions and attempting store access; only
      typed proposals reach separately authorized commands and graph processes receive no store
      handle or path. Falsifier: Let a graph node write priority directly; the no-direct-authority
      check must fail.
    falsified_by: >
      Let a graph node write priority directly; the no-direct-authority check must fail.
  - id: AC3
    text: >
      Claim: Domain enforcement does not depend on the installed graph runtime. Set and
      completeness: Run the enabled stdlib validator, authorization and gate-import entry points
      with the execution environment absent; ordinary enforcement remains usable and graph start
      reports runtime unavailable. Falsifier: Import LangGraph from authorization; the isolated-
      enforcement command must fail.
    falsified_by: >
      Import LangGraph from authorization; the isolated-enforcement command must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Replaceable LangGraph execution adapter. Deliver the normal function needed by the running factory journey.

## Context

W28 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Actual LangGraph is required by owner Telegram 28848 and R34. Release 1 uses a nonpersistent
graph, with no persistent checkpointer or database access from graph/model execution. Veldo
owns cycle/action identity and domain results. 0044 checkpoint connection/isolation and
recovery are Release 2.

Stated limit: Release 1 runs graph execution as the same account with no OS-user boundary
(owner rulings; hardening is later). What the adapter hands the graph child leads nowhere near
the repository: a fixed environment, no inherited descriptors, a path-free closed request, and a
content-addressed runner copy and working directory outside every repository. A deliberately
hostile node can still reach the domain process through /proc (its working directory and open
descriptors) as the same account. The proof keeps that limit visible in its own row. Real
confinement, through a separate mount and process view or a separate account, is Release 2.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 checkpoint
recovery and AC3 recovery without runtime moved to Release 2; broad AC1 replacement-
equivalence matrix moved to Release 2. Actual nonpersistent LangGraph and replaceable
interface remain; 0044 is not an MVP dependency. The criteria, declared evidence universe,
Context and Notes above now carry only the retained function. No specification status or
historical proof was changed.

2026-09-23 implementation (partial): register the AC3 negative controls in the existing
`scripts/check_teeth_mutations.py` driver (the authorized footprint exception, also listed in
the machine-readable footprint), with three distinct mutations for the isolated-enforcement row,
two for unavailable graph start, and fresh unmutated controls. AC1 and AC2 are not built: the
actual LangGraph runtime is not installed because its dependency closure conflicts with C16
and needs an owner decision, recorded in proof/VELDO-0043/README.md. No criterion, status or
historical proof was changed.

2026-09-23 implementation: AC1 and AC2 built on the actual LangGraph runtime after the owner
approved xxhash, langsmith, langgraph-sdk (Telegram 28927 answering 28926) and orjson as named
exceptions, with dependencies of chosen software approved automatically (28929) and every pin
at the latest compatible release (28931). The lock is the data module
`.veldo/control_graph_lock.py`, inside the existing `.veldo/control_graph*.py` footprint; the
per-account runtime is built by `.veldo/control_graph_install.py`. Eight more finding 43
negative controls are registered in `scripts/check_teeth_mutations.py`. No criterion, status or
historical proof was changed.

2026-09-23 independent-review fixes: the runtime holds only locked distributions (installed
without pip); an over-deep answer is a named refusal; requests and answers are closed schemas
with exact digests, versioned supplied results, text notes and no filesystem path; suspend and
cancel execute the compiled graph and the runtime label comes from what ran; the runner is
launched from a content-addressed copy outside every repository, with the /proc reach recorded
as the stated limit in Notes. Eleven more finding 43 negative controls are registered. No
criterion, status or historical proof was changed.
