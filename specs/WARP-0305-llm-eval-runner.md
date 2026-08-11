---
schema: veldo.spec/v1
id: WARP-0305
title: LLM/eval runner (reference) - B3 of PLAN-0003
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0003
work: B3
plan_revision: 2
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A generic LLM/eval runner ships at
      engine/scripts/runners/llm/veldo_llm_runner.py. It reads an eval
      journey (JSON, a prompt_id, a graded set of cases each with an id, an
      input, and behavioral graders, optional cost and latency budgets, a
      min_pass_rate, and an optional baseline of a prior prompt_id and its passed
      cases). It drives each case through a provider callable that returns an
      output plus a cost and latency, applies the case's graders, aggregates the
      pass rate and total cost and latency, and checks them against the budgets.
      It exits 0 when every budget and the pass rate hold and no regression is
      found, and exits 1 with the failing case, budget, or regression named. The
      provider is a seam: the reference ships a deterministic fake provider that
      returns each case's canned response, so the runner is gradeable with no
      live model, and an adopting repo passes its own provider.
  - id: AC2
    text: The graders are real behavioral assertions and fail loud. A contains
      grader fails when its substring is absent, not_contains when its substring
      is present, equals on any difference, and regex when the pattern does not
      search the output; each failure names the case and the grader. A total cost
      or total latency over budget fails with the measured total, and an
      aggregate pass rate below min_pass_rate fails with the observed rate. A
      case whose graders all hold counts as passed; a case with no graders is a
      journey error (a case that asserts nothing is not proof), reported loud.
  - id: AC3
    text: Regression on prompt change is detected. When the journey's prompt_id
      differs from the baseline's prompt_id, any case listed in the baseline's
      passed set that now fails is reported as a regression naming the case and
      both prompt_ids, and the run fails even if the new prompt's other cases
      pass. A passing fixture (all cases pass under the new prompt, no regression,
      budgets met) and a deliberately-failing fixture (the new prompt breaks a
      case that passed under the baseline prompt) ship under
      engine/scripts/runners/llm/fixtures/; the passing fixture exits 0
      and the failing fixture exits 1 with the regressed case named.
  - id: AC4
    text: The runner's control logic is unit-tested in scripts/selftest.py with
      no external dependency - it drives the runner over both shipped fixtures
      with the deterministic fake provider (pass to exit 0, fail to exit 1 with
      the regression named), and the pure helpers are exercised directly for both
      outcomes (each grader kind true and false, a cost and a latency budget met
      and exceeded, a pass rate at and below min_pass_rate, a regression present
      and absent, and a case with no graders reported loud). All prior selftest
      cases keep passing and the gate stays green.
  - id: AC5
    text: The runner is generic - zero company or product names in the runner,
      fixtures, wrapper, or README - and .veldo/capabilities.yaml (template and
      repository instance, kept byte-identical) declares it status reference (a
      shipped reference an adopting repo wires to its eval gate slot with its own
      model provider; the veldo repo does not run it), never mechanical. The
      docs-hygiene, secret, lint, and template-sync gates stay green.
required_evidence: [unit, operational]
rollback: git revert; B3 adds a new runner directory under engine, a
  selftest block, and an honest capabilities entry (template and instance) - no
  protected gate script or enforcer is touched, so reverting removes the
  reference artifact and its unit block with no effect on any running gate; the
  prior selftest cases are unchanged.
---

## Intent

PLAN-0003 (the batteries) ships a reference runner for every common product
surface. B3 is the LLM and evaluation surface. The outcome that should become
true is that a repository shipping model-driven behavior can drop in a generic
runner, describe a graded eval set and the behavioral assertions each case must
satisfy, set cost and latency budgets, and get proof that the behavior holds and
that a prompt change did not regress a case that used to pass. Model behavior is
the one product surface where "it ran" says nothing about "it is correct", and a
prompt edit can silently break a case far from the one it targeted. This runner
grades the set, budgets the spend and the latency, and fails a regression.

## Context

B3 of PLAN-0003, feature F2 (behavioral and eval surfaces), pulled against plan
revision 2. The runner follows the shipped runners' pattern: a generic reference
under engine/scripts/runners/, a fixture PAIR (passing and
deliberately-failing), and a unit test that gate-tests the control logic with no
external service. A live model is nondeterministic and costs money, so it cannot
run in the every-commit gate; the model is therefore a PROVIDER seam - a callable
returning an output plus a cost and latency. The reference ships a deterministic
fake provider that returns each case's canned response from the fixture, so the
grading, the budgets, and the regression detection are gate-tested with no live
model, and an adopting repo passes its own provider (which calls its real model)
unchanged. The distinctive assertion is regression on prompt change: when the
prompt_id moves off the baseline, a case that passed under the old prompt but
fails under the new one is a regression and fails the run, because a prompt edit
that quietly breaks a working case is exactly the defect a happy-path eval misses.

## Out of scope

Calling any real model or embedding provider (the provider seam is where a repo
plugs that in; the reference is deterministic by design). Scoring models,
semantic similarity, or LLM-as-judge graders beyond the textual behavioral
assertions here (an adopting repo adds its own grader kinds). Prompt management
or versioning systems. Statistical significance of eval deltas. Wiring the veldo
home repository's gate to this runner: the home repo ships no model-driven
behavior of its own, so the runner ships as a reference marked status reference
and is not run in the home gate.

## Notes

A case's graders are ANDed: the case passes only if every grader holds. A case
with no graders is a journey error, not a pass, because a case that asserts
nothing is not proof (this mirrors the API runner review note made load-bearing
here). Budgets are totals across the set: max_total_cost, max_total_seconds, and
min_pass_rate; each is optional and any present one must hold. The baseline
records the previous prompt_id and the set of case ids that passed under it; a
regression is a baseline-passed case that now fails, evaluated only when the
current prompt_id differs from the baseline prompt_id. The fake provider reads a
per-case fake block (output, cost, latency); an adopting repo replaces it by
importing run() and passing provider=its_own_callable, whose signature is
provider(case) returning a dict with output, cost, and latency.
