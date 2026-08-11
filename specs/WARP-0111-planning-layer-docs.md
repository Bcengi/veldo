---
schema: veldo.spec/v1
id: WARP-0111
title: Method v2.0 Stage 0, setup planning sections, PM training module, runbook planning chapter
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0001
work: W11
plan_revision: 3
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The method document is version 2.0 and adds a Stage 0 planning stage,
      placed ahead of Stage 1, that describes Product Plans, the plan contract
      (veldo.plan/v1), the ordered work DAG with declared dependencies, the ready
      frontier, and promotion from a standalone spec to a planned one; the two
      lanes (standalone for bugs and isolated work, planned for iterations) are
      stated so Stage 0 does not contradict the existing "specification is the
      unit of work" principle.
  - id: AC2
    text: The setup document gains a Product Plan contract subsection and an
      operating-the-planning-layer subsection covering create, refine, approve,
      revise with impact, status/burn-down, regression, and release check; its
      skill list in section 4.3 includes /veldo:plan.
  - id: AC3
    text: A PM training module (docs/training/planning-layer.md) teaches a product
      manager to drive the planning layer end to end - create a plan, decompose
      it into specs, manage the ready frontier, and read status and metrics - is
      registered in docs/manifest.yaml with a parseable version line, and is
      cross-linked from product-manager.md.
  - id: AC4
    text: The runbook gains a keystroke-exact planning chapter (a new Runbook in
      Part I plus a Part V administration entry) that operates the planning layer
      day to day.
  - id: AC5
    text: Every /veldo:plan sub-verb and every .veldo/plan.py command shown in the
      new documentation exists in packs/claude/skills/plan/SKILL.md or .veldo/plan.py
      (create, refine, approve, pull, revise, status, regression, release for the
      skill; status, release-check, impact, regression, bundle, run-check, hash
      for plan.py); no capability is described as more automatic than
      .veldo/capabilities.yaml declares it (planning dialogue is procedure, the
      run-time refusal and plan hash are mechanical, the gate regression slot is
      per-repo reference wiring).
  - id: AC6
    text: The full gate is green - docs hygiene passes (ASCII only, no em, en, or
      double hyphens, and zero company or product references in docs/ and
      packs/claude/), the contract selftest passes, and specs/index.md regenerates as a
      no-op with the plan burn-down reflecting W11 as pulled.
required_evidence: [unit, operational]
rollback: git revert; every change is additive documentation - a new Stage 0 in
  the method, new subsections in setup, a new training module and its manifest
  entry, a new runbook chapter, a plugin minor-version bump, and re-rendered
  PDFs; no code, contract, or policy changes, so reverting the commit restores
  the prior document set with no machinery impact.
---

## Intent

The planning layer shipped across W1 through W8 (the Product Plan contract and
validator, the /veldo:plan skill, /veldo:run plan integration, regression
mechanics, the event envelope and metrics), but the human-facing documents
still describe VELDO as a pure stream of specifications. A person reading the
method, the setup guide, the training series, or the runbook cannot learn that
product work is now planned holistically first and decomposed second. W11 closes
that gap: it teaches the planning layer that already exists, and nothing more.

The controlling constraint is honesty. The documents must describe the machinery
that actually shipped, at the automation level `.veldo/capabilities.yaml`
declares, and must not resolve the open question O4 (whether the layer can carry
project-management judgment) that the W12 dogfood is meant to settle. The
project-manager training document's conditional stands until that proof exists.

## Context

The shipped surfaces this documentation must stay consistent with:

- `plans/TEMPLATE.md` and `plans/PLAN-0001-*.md` - the plan shape and a live
  example (outcomes, non_goals, constraints, feature_tree, an ordered work DAG,
  regression journeys, release, open_decisions).
- `packs/claude/skills/plan/SKILL.md` - the /veldo:plan sub-verbs: create, refine,
  approve, pull, revise, status, regression, release, plus the two-lanes and
  promotion rules.
- `.veldo/plan.py` - the mechanical verbs: status, release-check, impact,
  regression, bundle, run-check, hash.
- `packs/claude/skills/run/SKILL.md` - the planned-spec preflight (run-check refusal,
  context bundle, plan hash into proof).
- `.veldo/capabilities.yaml` - the truth about what is mechanical, reference,
  procedure, or absent; the documents defer to it.

## Out of scope

No machinery changes: no edits to validators, policy, guards, skills, or the
plan module. No new enforced rule, therefore no new selftest negative. The W12
dogfood and any claim that project management is fully carried by the layer are
out of scope; the conditional in project-manager.md and training-guide.md stays.
The plugin PRICES-style contracts and any company product remain unmentioned;
docs stay generic.

## Notes

Version bumps: method 1.3 to 2.0 (major, for the new stage and the two-lane
model), setup 2.8 to 2.9, runbook 1.3 to 1.4, product-manager 1.0 to 1.1,
training-guide 1.1 to 1.2, and a new planning-layer training module at 1.0. The
plugin minor version bumps by the shipping convention. PDFs are re-rendered from
the changed documents and the document map; PDFs are a manual release artifact,
not gate-enforced.
