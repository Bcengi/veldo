---
schema: veldo.spec/v1
id: WARP-1007
title: Document to plan - a requirements page kicks off a whole plan of epics and children
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W7
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A draft_plan_from_requirements function turns a structured requirements page into
      a veldo.plan/v1 DRAFT: it reads the page through the shipped intake seam, parses its
      Outcomes and its work breakdown from the shipped requirements template (reusing the
      WARP-0607 parse_requirements), resolves the target repo via the reused routing
      resolver, and renders a plan with outcomes derived from the page's Outcomes and one
      work item per named deliverable, bound to the resolved repo, with the source page
      linked. It fails CLOSED by name when the routing signal is missing, unknown, or
      ambiguous, exactly like the spec intake.
  - id: AC2
    text: >
      The generated plan is a valid veldo.plan/v1 (it passes the plan schema check) and is
      a DRAFT (status: draft) the human refines and approves before any work is built,
      mirroring the human validation gate: a draft plan is not executed, and approval
      (status draft to ready with approved_by) stays a human act. The generator is a
      deterministic non-LLM structural transform (page sections to plan sections), reusing
      the requirements parsing and routing, adding no second parser and no agent call;
      page content is untrusted input, sanitized (no front-matter injection).
  - id: AC3
    text: >
      The chain is complete end to end: a kickoff ticket that references a requirements
      page yields a plan draft (this item), which once approved the live epic mirror
      (WARP-1006) projects onto a real Jira epic and one child issue per work item, and
      each child, once assigned to Agent and Approved-for-dev, flows through the inbound
      bridge, the promote gate, and the fleet. This item supplies the missing generation
      step; it wires no new tracker writes.
  - id: AC4
    text: >
      Gate-tested offline over a fixture requirements page (and the FakeTracker) with
      teeth: a resolvable page renders a schema-valid plan draft bound to the repo whose
      outcomes match the page's Outcomes and with one work item per named deliverable and
      the page linked; an unresolvable page (missing/unknown/ambiguous routing) is refused
      by name; a malicious page cannot inject plan front matter; and the rendered plan
      parses as a valid veldo.plan/v1. Non-tautological (the routing signal present renders,
      removed it refuses).
  - id: AC5
    text: >
      capabilities.yaml gains an honest entry for the document-to-plan generator
      (mechanical, its shipped home) in both byte-identical copies; every edited
      ENGINE_GLOBS file is re-synced byte-identical across engine and all seven
      packs (template-sync and pack-drift pass). The full gate is GREEN, RULE #1 is clean,
      no protected path is touched, and the change lands in the canonical two-commit shape.
required_evidence: [unit]
rollback: >
  Revert the commit. The generator is additive (a new function + a template + a selftest)
  and nothing runs it automatically; removing it leaves requirements intake producing a
  single spec draft exactly as before, with no migration.
---

## Intent

This is the last missing piece of the founder's loop: a requirements document should
kick off a WHOLE plan, not a single spec. A kickoff ticket points at a requirements
page; VELDO drafts a plan from it; the human approves the plan; and the already-built
live epic mirror turns that plan into an epic and child tickets, each of which then
flows through the autonomous loop. This item supplies the document-to-plan generation
that sits between the page and the epic.

## Context

- Reuse: .veldo/tracker_intake.py already has draft_spec_from_requirements +
  parse_requirements + the Confluence intake adapter + _fm_safe sanitization and the
  routing resolver. draft_plan_from_requirements is the sibling that renders a PLAN
  instead of a single spec (outcomes from the page's Outcomes; a work item per named
  deliverable). Read plans/TEMPLATE.md for the veldo.plan/v1 shape.
- The plan it renders is a DRAFT (status: draft); it is refined and approved by a human
  (draft to ready + approved_by), matching how a spec draft is promoted. The machine
  never approves a plan (PLAN-0010 NG1).
- The projection onto a real epic + children is WARP-1006 (already shipped); this item
  produces the plan the epic mirror consumes.
- Deterministic non-LLM structural transform, fail closed on routing, page content
  untrusted and sanitized. A requirements-page template already ships
  (engine/confluence-requirements-template.md); extend it if the plan needs a
  work-breakdown section, keeping it a template.

## Out of scope

- No live Jira in the gate; the FakeTracker + a fixture page drive every assertion.
- No auto-approval or auto-build of the drafted plan (the human approves). No change to
  the runner, bridge, promote gate, reassign/links, or epic/child creation.

## Notes

- Keep draft_plan_from_requirements a pure function so the gate drives it with a fixture
  page and a temp config. Fail closed on an unresolvable page; sanitize page content so
  it cannot inject plan front matter. Validate the rendered plan against the plan schema.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Today is 2026-07-21; regenerating specs/index.md restamps its date header.
