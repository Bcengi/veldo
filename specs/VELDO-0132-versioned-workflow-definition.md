---
schema: veldo.spec/v1
id: VELDO-0132
title: Versioned workflow definitions consumed by LangGraph
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W95
plan_revision: 3
depends_on: [VELDO-0035, VELDO-0043]
placement: [contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - "scripts/suites/*_veldo_0132_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0132-versioned-workflow-definition.md"
  - "specs/index.md"
  - "proof/VELDO-0132/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Veldo stores immutable workflow revisions with schema, node/edge identity and validated
      configuration references. Set and completeness: Enumerate fields from the workflow schema:
      identity/version, entry/terminal nodes, registered step kinds, ports/transitions, role/tool
      configuration references, budgets and bounded loop conditions where allowed. Reject dangling
      edges, unknown node types, missing references and unbounded cycles; authorized edits create
      new revisions with prior bytes retained. Falsifier: Accept an edge to a nonexistent node; the
      workflow-validation check must fail.
    falsified_by: >
      Accept an edge to a nonexistent node; the workflow-validation check must fail.
  - id: AC2
    text: >
      Claim: Each LangGraph cycle executes one exact accepted workflow revision. Set and
      completeness: Run an actual graph built from a stored definition containing grooming, owner
      wait, assignment and result handling; compare node/transition trace to the stored digest. Save
      a new revision mid-cycle and observe that cycle retaining its original binding while a later
      authorized cycle uses the new revision. Falsifier: Read mutable canvas state during an active
      cycle; the pinned-workflow trace comparison must fail.
    falsified_by: >
      Read mutable canvas state during an active cycle; the pinned-workflow trace comparison must
      fail.
  - id: AC3
    text: >
      Claim: Canvas serialization and load preserve the workflow data without executing it. Set and
      completeness: Save and reload a definition through the authenticated API and editor, compare
      canonical semantic node/edge/configuration data including layout metadata separated from
      execution semantics, and inspect zero dispatch/provider/shell calls caused by editing or
      loading. Falsifier: Launch a worker while saving an edge; the edit-without-execution check
      must fail.
    falsified_by: >
      Launch a worker while saving an edge; the edit-without-execution check must fail.
  - id: AC4
    text: >
      Claim: Workflow execution remains bounded by ordinary Veldo authorization and result
      validation. Set and completeness: Attempt a definition selecting an unauthorized role,
      exceeding the cycle budget or asserting completion; run it through actual LangGraph and
      require current proposal/eligibility checks and named refusal, with no direct domain write.
      Falsifier: Let a terminal graph node set spec.shipped directly; the no-workflow-authority
      check must fail.
    falsified_by: >
      Let a terminal graph node set spec.shipped directly; the no-workflow-authority check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Store the workflow/pipeline as versioned Veldo data that LangGraph executes and the UI canvas
can edit without becoming a runtime.

## Context

W95 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: an authorized editor saves a workflow definition as plain versioned data (identity and
  version, entry and terminal nodes, registered step kinds, ports and transitions, role and tool
  configuration references, budgets, bounded loops). Veldo validates it and stores it as a new
  immutable revision, keeping the earlier bytes. Each LangGraph cycle binds one exact accepted revision
  when it starts and keeps it even if a new revision is saved while it runs. Saving and loading never
  dispatch work, call a provider or run a shell. A workflow's steps act only through ordinary proposals
  and eligibility checks and never write domain state themselves. AC3 is driven through the save and
  load interface that the authenticated API (VELDO-0130, its workflow save endpoint) and the editor
  (VELDO-0131, its canvas) call; those two specs exercise their own legs when they are built.
- Threat model: a definition with a dangling edge, an unknown step kind, a missing configuration
  reference or an unbounded cycle; an edit that overwrites an accepted revision in place; a running
  cycle that picks up an edit mid-run; editing or loading that launches work; and a definition that
  selects an unauthorized role, exceeds its cycle budget or asserts completion directly. The owner's
  account, the store and the installed LangGraph runtime are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); checkpoint
  recovery and resuming a cycle after a crash (Release 2); the API and editor themselves (VELDO-0130,
  VELDO-0131); forged rows in our own store and files planted in the installed directory.

## Notes

The owner requires a workflow/pipeline editor and LangGraph step runtime in Release 1
(2026-09-22; LangGraph inclusion in Telegram 28848). Domain schemas stay plain versioned data
and stdlib validated. The definition selects registered step types, transitions and
configuration references; it never embeds arbitrary shell, SQL or browser-executable
authority. Checkpoint recovery is Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 4, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-24: implemented on branch build-veldo-0132 (built on 5a5dfcd, origin/main merged). Three
new modules with byte-identical engine copies: control_workflow.py (the stdlib-validated definition
and its immutable revisions, saved and loaded without execution), control_workflow_cycle.py (cycles
bound to one exact revision, run one judged step per exchange on the actual LangGraph through the
VELDO-0043 adapter and the VELDO-0045 runtime, every step through the role, Gate and result checks)
and control_workflow_langgraph.py (the step kinds spliced into the runner). Suite
65_veldo_0132_workflow has 10 criterion rows and 5 region rows. Finding 132 in
scripts/check_teeth_mutations.py registers 26 mutations, among them each criterion's declared
falsifier, all rejected. scripts/suites/manifest.json gains suite 65, and requires.json is
regenerated. Every row was recorded red at 5a5dfcd, and one defect found during the build was
recorded red before its fix. The status stays ready. Proof: proof/VELDO-0132/.
